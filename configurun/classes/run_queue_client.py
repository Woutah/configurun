"""Implements RunQueueClient which forms a pair with RunQueueServer.py - this class acts as if it's an actual RunQueue
instance, but instead sends all function calls to a server on which the actual RunQueue instance is running
"""

import logging
import queue
import socket
import threading
import traceback

from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from PySide6 import QtCore

from configurun.classes.method_call_interceptor import (
    MethodCallInterceptedMeta, get_class_implemented_methods)
from configurun.classes.run_queue import RunQueue
from configurun.classes.run_queue_datatypes import (RSA_KEY_SIZE_BITS,
                                               AESSessionKeyTransmissionData,
                                               AuthenticationException,
                                               LoginTransmissionData,
                                               PickledDataType,
                                               PickleTransmissionData,
                                               PubKeyTransmissionData,
                                               StateMsgType,
                                               StateTransmissionData,
                                               Transmission, TransmissionType)

log = logging.getLogger(__name__)


def get_pyqt_signal_names(the_object : type) -> list[QtCore.SignalInstance]:
	"""
	Get all PySide6.QtCore.signals of an arbitrary object (by name)
	"""
	signals = []

	for signal_name in the_object.__dict__:
		if isinstance(the_object.__dict__[signal_name], QtCore.Signal):
			signals.append(signal_name)


	return signals

def no_function(*args, **kwargs): #pylint: disable=unused-argument
	"""Dummy function that does nothing"""
	pass #pylint: disable=unnecessary-pass

class RunQueueClient(RunQueue,
		    metaclass=MethodCallInterceptedMeta,
			intercept_list=get_class_implemented_methods(RunQueue),
			skip_intercept_list=get_pyqt_signal_names(RunQueue)):
	"""
	Each clients acts as if it is a runQueue - connecting to a server on which the actual runQueue is running.
	Each function of the runQueue is intercepted by this class and sent to the server (except the signals).

	NOTE: this class uses ```RunQueue```- which uses pyqt signals - make sure a main event loop is running
	(e.g. app.exec()) when using instances of this class

	NOTE: if the client is not connected to a server - the method-interceptor instead returns None (and logs a warning)

	As soon as a connection is established, the client will start listening to the server for signals and method calls.
	Also, the reset-signal is emitted from the queue, indicating that all models should be reset.
	"""

	authenConnectionStateChanged = QtCore.Signal(bool) #Emitted when the authenticated connection state changes -
		# True if connected and authenticated, False if either disconnected or not yet authenticated


	def __init__(
			self
		) -> None:
		"""Initializes the RunQueueClient

		Has no args, since RunQueue will be running on server-side, settings attributes here would be useless.
		All function calls will be intercepted and sent to the server.
		"""
		super().__init__(target_function=no_function)
		self._server_ip = None
		self._server_port = None
		self._socket : socket.socket | None = None
		self._authenticated = False
		self._password = None

		#Generate a public/private key pair for the server
		self._rsa_key : RSA.RsaKey = RSA.generate(RSA_KEY_SIZE_BITS)
		self._public_key = self._rsa_key.publickey()
		self._private_key = self._rsa_key
		self._private_rsa_cipher = PKCS1_OAEP.new(self._rsa_key)

		#Created based on the session key received from the server
		self._listen_thread = None

		self._test_thread = None
		self._aes_session_key = None

		# self._method_return_queue = queue.Queue() #When the server responds - the listener thread will put the
			# result in this queue - should
		self._method_response_dict : dict[int, queue.Queue] = {} #When the server responds - the listener thread will
			#put the result in this queue - keys are method ids, values are the result of the method call
		self._method_reponse_dict_lock = threading.Lock()
		self._method_id_counter = 0 #Used to keep track of which function call is which

		self._connected_or_connecting = False #Used to make sure that we're only attempting 1 connection at a time

		self._disconnect_flag = True #Whether to stop listening to the server

	def force_stop(self):
		#TODO: implement
		raise NotImplementedError("Not implemented yet")

	def is_connected(self):
		"""Returns whether the client is currently trying to connect to the server or is connected to the server

		Returns:
			bool: Whether the client is currently trying to connect to the server or is connected to the server
				This doesn't indicate that the connection has been accepted by the server yet
		"""
		return self._connected_or_connecting

	def is_connected_and_authenticated(self) -> bool:
		"""Returns whether an authenticated connection to the server has been established

		Returns:
			bool: Whether an authenticated connection to the server is currently active
		"""
		return self._authenticated

	def _interceptor(self, function_name: str, *args, **kwargs):

		log.debug(f"Intercepted call to RunQueue function {function_name}")# with args: {args} and kwargs: {kwargs}")
		if self._socket is None or not self._authenticated or self._aes_session_key is None:
			log.warning(f"Could not pass on method call to {function_name}, to server, as no (authenticated) connection\
	       		to server has been established yet - returning None")
			return None
		# Send a state message to the server of the intercepted call
		# Transmission.send(
		# 	self._socket,
		# 	StateTransmissionData(
		# 		state_msg_type = stateMsgType.general_msg,
		# 		state_msg = f"Client Intercepted & passed on call to RunQueue function {function_name} with args:
		# 			#{args} and kwargs: {kwargs}"
		# 	),
		# 	aes_cypher_key= self._aes_session_key
		# )

		with self._method_reponse_dict_lock:
			self._method_id_counter += 1 #Increment the method id counter
			self._method_response_dict[self._method_id_counter] = queue.Queue(maxsize=1) #This makes it easy to wait
				# for the result of a method call - note that only 1 response is possible so queue size is 1
			method_call_id = self._method_id_counter

		log.debug(f"Sending intercepted call to RunQueue function {function_name} with args: {args} and kwargs: \
	    	{kwargs} with id {method_call_id} to server.")
		Transmission.send(
			self._socket,
			PickleTransmissionData(
				(
					PickledDataType.METHOD_CALL, #Indicates a triplet of the form(request_id, function_name, args, kwargs)
					(
						method_call_id,
						function_name,
						args,
						kwargs
					)
				)
			),
			aes_cypher_key= self._aes_session_key
		)

		if function_name == self.get_command_line_output.__name__: #TODO: might be a more elegant way to do this, maybe
			# request data in multiple chunks? Probably best to limit console-mirror-size as >50mb files
			# are not very UI-friendly
			self._await_method_response(method_call_id, timeout=20) #Since log file can be quite large, wait longer

		return self._await_method_response(method_call_id, timeout=5) #Wait for the server to respond to the method call
			#and return the result

	def _await_method_response(self, function_response_id : int, timeout : float):
		"""
		Wait for server response after a function call. Response is automatically put in reponse_dict by the server-
		listener. If, after timeout, no response is received in this dict, a TimeoutError is raised.
		"""
		return_queue = self._method_response_dict[function_response_id]
		try:
			ret = return_queue.get(block=True, timeout=timeout)
			log.info(f"Received response from server for method call with id {function_response_id}, response: {ret}")
		except (TimeoutError, queue.Empty) as exception: #If the queue is empty, then the server did not respond in time
			raise TimeoutError(f"Timeout while waiting ({timeout}s) for response of method call with \
		    	id {function_response_id}") from exception
		finally: #Always clean up the queue to no longer listen for this id
			with self._method_reponse_dict_lock:
				del self._method_response_dict[function_response_id]

		if isinstance(ret, Exception): #Do not return exception types -> raise them instead #TODO: is this what we want?
			ret.args = (f"Exception raised by server while executing method call with id {function_response_id}: \
	       		{ret.args[0]}",) + ret.args[1:]
		return ret


	def get_connection_info(self):
		"""
		Returns a tuple of (server_ip, server_port, server_password) if connected, else tuple of (None, None, None)
		"""
		if self._socket is None:
			return (None, None, None)
		return (self._server_ip, self._server_port, self._password) #TODO: hashed password

	def disconnect_clean_server(self):
		"""
		Tries to disconnect socket if it is still active and resets all variables
		"""
		self._disconnect_flag = True
		self._server_ip = None
		self._server_port = None
		if self._socket is not None:
			try:
				self._socket.close()
			except OSError as exception:
				log.error(f"Error while closing socket: {exception}")
		self._socket = None
		self._aes_session_key = None
		if self._authenticated: #Only emit signal if we were connected before
			self.authenConnectionStateChanged.emit(False)
		self._authenticated = False
		self._connected_or_connecting = False
		if self._listen_thread is not None:
			#Wait for the listening thread to finish last iteration - then join it
			self._listen_thread.join()
			self._listen_thread = None

		#TODO: stop threads

	def connect_to_server(self, server_ip: str, server_port: int, password : str) -> None:
		"""Try to connect to server with provided ip, port and password. If connection is successful, the client will
		start listening to the server for Transmissions.

		NOTE: this function will overwrite any existing connection to a server

		Args:
			server_ip (str): The server ip where RunQueueServer is running
			server_port (int): The server port where RunQueueServer is running
			password (str): The password to use to authenticate with the server
		"""
		try:
			self.disconnect_clean_server()
			self._connected_or_connecting = True
			self._authenticated = False
			self._disconnect_flag = False
			self._server_ip = server_ip
			self._server_port = server_port

			#Connect tcp socket to server
			self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self._socket.connect((self._server_ip, self._server_port))

			#Send public key to server
			Transmission.send(
				self._socket,
				PubKeyTransmissionData(
					self._public_key.export_key()
				)
			)


			received = Transmission.receive(
				self._socket,
				None
			)
			if received.transmission_type != TransmissionType.SESSION_KEY:
				log.error("Did not receive AES session key from server")
				#Check if remote server closed connection
				if received.transmission_type == TransmissionType.STATE:
					state = StateTransmissionData.from_transmission_bytes(received.transmission_data)
					log.error(f"Server returned: {state.state_msg_type.name} - {state.state_msg}")
					raise AuthenticationException(f"Server returned: {state.state_msg_type.name} - {state.state_msg}")
					#TODO: login-exception instead of Exception
				raise AuthenticationException("Did not receive AES session key from server during login process")

			#Decrypt the session key using the private key
			encrypted_aes_session_key = AESSessionKeyTransmissionData.from_transmission_bytes(received.transmission_data)
			aes_session_key = self._private_rsa_cipher.decrypt(encrypted_aes_session_key.encrypted_session_key)
			# self._aes_cipher = AES.new(aes_session_key, AES.MODE_EAX)

			log.info(f"Aes session key: {aes_session_key} - now verifying password")

			#=========== From here on out, all communication is encrypted ===========
			#Send login data
			Transmission.send(
				self._socket,
				LoginTransmissionData(
					password
				),
				aes_session_key
			)

			self._aes_session_key = aes_session_key
			#Wait for response
			received = Transmission.receive(
				self._socket,
				aes_session_key
			)
			if received.transmission_type != TransmissionType.STATE:
				log.error("Did not receive login response from server")
				raise AuthenticationException("Did not receive login response from server") #TODO: login-error

			state_msg = StateTransmissionData.from_transmission_bytes(received.transmission_data)
			if state_msg.state_msg_type == StateMsgType.LOGIN_ERROR:
				raise AuthenticationException(f"Login rejected by server: {state_msg.state_msg}")
			elif state_msg.state_msg_type == StateMsgType.LOGIN_ACCEPTED:
				log.info("Login accepted by server")




			if self._listen_thread is None:
				log.info("Starting server-listening thread...")
				self._listen_thread = threading.Thread(target=self._listen_to_server)
				self._listen_thread.start()
				log.info("Started server-listening thread...")

			self._authenticated = True
			self._password = password #TODO: hash password twice.
			self.authenConnectionStateChanged.emit(True)
			self.queueResetTriggered.emit() #Emit the reset signal so all models re-request all data
			log.info("Connected to server and authenticated. Can now request/receive/transmit data from/to server.")
		except Exception as exception:
			#Just pass on the exception
			self.disconnect_clean_server() #Clean up
			raise exception

		# self._test_thread = threading.Thread(target=self._send_to_server)
		# self._test_thread.start()



	def _listen_to_server(self):
		"""
		Start listening to the server for Transmissions. E.g.:
		- StateTransmissionData -> Server is sending a state message
		- PickleTransmissionData -> Server is sending a pickled object - for example - a result of a function call or
			a Signal object
		"""
		log.info("Started continuously listening to server")
		try:
			while not self._disconnect_flag:
				received = Transmission.receive(
					self._socket, #type: ignore
					aes_cipher_key=self._aes_session_key
				)

				if received.transmission_type == TransmissionType.STATE:
					data = StateTransmissionData.from_transmission_bytes(received.transmission_data)
					log.info(
						f"Received state from server: {data.state_msg_type.name} - {data.state_msg}"
					)
				elif received.transmission_type == TransmissionType.PICKLED_OBJECT:
					try:
						data = PickleTransmissionData.from_transmission_bytes(received.transmission_data)
						unpickled_data = data.unpickled_data #type: ignore
						assert isinstance(unpickled_data, tuple), "First element is the type of the data, \
							should be tuple"

						if unpickled_data[0] == PickledDataType.METHOD_RETURN:
							#The server is sending the result of a function call
							#Unpack the data
							function_call_id, result = unpickled_data[1]
							with self._method_reponse_dict_lock:
								if function_call_id not in self._method_response_dict:
									log.error(f"Received function call result with id {function_call_id} - but no \
										function call with that id was made")
									continue
								self._method_response_dict[function_call_id].put(result, block=True)
						elif unpickled_data[0] == PickledDataType.SIGNAL_EMIT:
							#The server is sending a signal
							#Unpack the data
							signal_name, args = unpickled_data[1]

							#Get signal by name
							signal : QtCore.SignalInstance = getattr(self, signal_name)
							log.debug(
								f"Received signal {signal_name} from server - resulting in a re-transmit of signal \
									{signal} of type {type(signal)}"
							)
							assert isinstance(signal, QtCore.SignalInstance)
							#Emit the signal
							signal.emit(*args) #type: ignore
						else:
							log.error(f"Received pickled data of type {unpickled_data[0].name} - which is not \
		 						supported (at the client side)")
					except Exception as exception: # pylint: disable=broad-exception-caught
						log.error(f"Error while unpickling pickle-transmission from server - {type(exception)}: \
							{exception}")
						traceback.print_exc()

		except Exception as exception: # pylint: disable=broad-exception-caught
			log.error(f"Error while listening to server: {exception} - disconnecting")
			self.disconnect_clean_server()
			return
