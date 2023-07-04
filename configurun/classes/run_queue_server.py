"""
Forms a pair with RunQueueClient - this class runs on the server side and handles all incoming connections.
It contains a RunQueue object to/from which all data is transmitted/received using the connected clients.
"""


import hashlib
import logging
import os
import socket
import threading
import time
import typing

import dill
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
import PySignal

from configurun.classes.run_queue import (WORKSPACE_RUN_QUEUE_SAVE_NAME,
                                          RunQueue, WorkspaceInUseException)
from configurun.classes.run_queue_datatypes import (
    AES_EMPTY_KEY, RSA_KEY_SIZE_BITS, AESSessionKeyTransmissionData,
    AuthenticationException, ClientData, LoginTransmissionData,
    PickledDataType, PickleTransmissionData, PubKeyTransmissionData,
    StateMsgType, StateTransmissionData, Transmission, TransmissionType)

log = logging.getLogger(__name__)
DATA_RECEIVE_TIMEOUT = 0.5 #Seconds of checking for new data before timing out to check if the server should stop

class RunQueueServer():
	"""
	A wrapper around a runqueue that opens up a socket an listens for a client to connect.
	RunQueueClient will run client-side and will emulate an instance of the RunQueue class by interfacing with the
	actual runqueue running on the server.

	NOTE: this class assumes that all information for the runqueue is transmitted to the ui via signals - or by
	the ui explicitly calling the functions of the runqueue. All signals in the runqueue are automatically connected
	to the emit_signal function of this class. All function calls on the client side are automatically forwarded to the
	server side.

	Call RunQueueServer.run() after instantiating the class to start the server.
	"""
	_salt = b"\xe6F\xd9\x8f\x15tS5H\xd2e\x82='\x18w\xac\xf1\xfd\x0c\x9c\x89\xf3rMX\xfc\xa1\xea\x8cm\xa2" #Random salt

	def __init__(self,
			run_queue: RunQueue,
			password : str,
			hostname : str = "",
			port : int = 5454,
			workspace_path : str = ""
		) -> None:
		"""
		Args:
			run_queue (RunQueue): The runqueue to use
			password (str): The password to use for authentication
			hostname (str, optional): The hostname to bind to. Defaults to "".
			port (int, optional): The port to bind to. Defaults to 5454.
			workspace_path (str, optional): The path to the workspace.
				Defaults to "". If none/empty, the workspace will be saved/loaded from/to '~/Configurun-Server/'
		"""

		self._run_queue = run_queue #Thread-safe run-queue, as long as we interface using only the provided functions


		self._workspace_path = workspace_path
		if workspace_path is None or len(workspace_path) == 0:
			self._workspace_path = os.path.join(os.path.expanduser("~"), "Configurun-Server")
			log.info(f"Using default workspace path: {self._workspace_path}")

		if not os.path.isdir(self._workspace_path):
			log.info(f"Creating workspace directory {self._workspace_path}")
			os.makedirs(self._workspace_path)

		try:
			self._run_queue.set_workspace_lock(self._workspace_path)
		except WorkspaceInUseException:
			log.warning(f"Workspace {self._workspace_path} is already in use")
			#Ask the user if they want to continue using the workspace using cmd input
			while True:
				choice = input(f"Workspace {self._workspace_path} seems to be in use by another instance of the "
		   			f"Configurun-app. Using this workspace anyway might overwrite existing save-files, or output "
					f" of this process might be overwritten by the other process. Do you want to continue anyway? (y/n): ")
				if choice.lower() == "y":
					break
				elif choice.lower() == "n":
					#re-raise the exception
					raise
				else:
					print("Invalid choice - please enter 'y' or 'n'")

		self._initial_run_queue_load() #Load the run-queue from the workspace- might ask for user input if problem arises

		self._socket = None

		#Generate a public/private key pair for the server
		self._rsa_key : RSA.RsaKey = RSA.generate(RSA_KEY_SIZE_BITS)

		self._public_key = self._rsa_key.publickey().export_key()
		self._private_key = self._rsa_key.export_key()
		self._private_cipher = PKCS1_OAEP.new(self._rsa_key) #Used to decrypt data sent by the clients

		self._client_public_keys = {}
		self._cipher = None

		self.set_password_hash(self.get_password_hash(password=password))

		self._client_dict : dict[socket.socket, ClientData]= {}
		self._client_dict_lock = threading.Lock()

		self._connection_listener_thread = None
		self._is_terminating = False #To check whether the server is terminating (don't start doing new stuff)
		self._server_stop_flag = threading.Event() #To stop the server from running (does not always indicate termination)

		self._hostname = hostname
		self._port = port

		#============= Manage signal-triggered events =============
		for signal_name in self._run_queue.__class__.__dict__:
			# if isinstance(self._run_queue.__class__.__dict__[signal_name], QtCore.Signal): #Previous version used qt
			if isinstance(self._run_queue.__class__.__dict__[signal_name], PySignal.ClassSignal): #Use pysignal for server-side
				target_signal = getattr(self._run_queue, signal_name)
				target_signal.connect(lambda *args, signal_name=signal_name: self.emit_signal(signal_name, *args))

		log.info("Initialized RunQueueServer")

	def terminate(self):
		"""
		Closes the server socket and terminates all clients, saves the current run-queue to the workspace.
		"""
		#First check if there are any items running in the run-queue
		if self._run_queue.get_running_configuration_count() > 0:
			while True:
				user_input = input("There are still items running in the run-queue. Do you want to terminate anyway? (y/n): ")
				if user_input.lower() == "y":
					break
				elif user_input.lower() == "n":
					log.info("Server-termination cancelled.")
					return
				else:
					print("Invalid input - please enter 'y' or 'n'")
		#Save the run-queue to the workspace
		queue_dict = self._run_queue.get_queue_contents_dict(save_running_as_stopped=True)

		dill.dump(queue_dict, open(os.path.join(self._workspace_path, WORKSPACE_RUN_QUEUE_SAVE_NAME), "wb"))
		log.info("Terminating server...")
		self._run_queue.stop_autoprocessing() #Indicate to server that it should stop processing new items


		self._is_terminating = True #Make sure we don't start any new threads
		self._server_stop_flag.set() #Stop the connection-listener thread
		try:
			self.disconnect_all_clients()
		except TimeoutError:
			log.error("TimeoutError while waiting for clients to disconnect - continuing with shutdown anyway. "
		 		"Forcefully terminating socket...")

		if self._connection_listener_thread and self._connection_listener_thread.is_alive():
			self._connection_listener_thread.join(3) #Wait for the connection-listener thread to stop
			if self._connection_listener_thread.is_alive():
				log.error("Connection-listener thread did not stop in time... Quitting anyway.")

		if self._socket:
			self._socket.close()
			self._socket = None

		self._run_queue.stop_command_line_queue_emitter() #Stop the command-line queue emitter
		self._run_queue.release_workspace_lock(self._workspace_path)
		log.info("Server terminated")


		# self._run_queue.(os.path.join(self._workspace_path, WORKSPACE_RUN_QUEUE_SAVE_NAME))


	def _initial_run_queue_load(self):
		"""
		Should be called just after setting workspace.
		Tries to load the RunQueue contents from a file according to the filename that is used when the close-event is
		called. If the file does not exist, nothing happens.
		"""
		if os.path.exists(os.path.join(self._workspace_path, WORKSPACE_RUN_QUEUE_SAVE_NAME)):
			cur_items = self._run_queue.get_all_items_dict_snapshot_copy()
			if len(cur_items.keys()) > 0:
				#Ask user if he/she wants to overwrite.
				while True:
					user_input = input("Trying to load run-queue from the workspace, but the current run-queue is not "
					"empty. Do you want to load the run-queue from the workspace anyway? This will overwrite the "
					"currently loaded queue (y/n): ")
					if user_input.lower() == "y":
						break
					elif user_input.lower() == "n":
						raise RuntimeError("Cannot load run-queue from workspace - current run-queue is not empty")
					else:
						print("Invalid input - please enter 'y' or 'n'")

			path = os.path.join(self._workspace_path, WORKSPACE_RUN_QUEUE_SAVE_NAME)
			queue_contents_dict = dill.load(open(path, "rb"))
			self._run_queue.load_queue_contents_dict(queue_contents_dict)
			log.info(f"Loaded run-queue from {path}")
			# self.ui.runQueueWidget.load_from_file_popup
		else:
			log.info(f"No RunQueue save file found at {os.path.join(self._workspace_path, WORKSPACE_RUN_QUEUE_SAVE_NAME)}"
					", continuing with the current (empty) run-queue.")

	def stop(self):
		"""Inidicates to all running threads that the server should stop the connection
		NOTE: we can still call run() after calling stop() - this will restart the server
		"""
		self.disconnect_all_clients()
		self._server_stop_flag.set()


	def run(self):
		"""Starts the server and listens for connections
		"""
		if self._is_terminating:
			raise RuntimeError("Server is terminating - cannot start running the server now...")
		if self._connection_listener_thread is not None:
			raise RuntimeError("Server is already running")
		if self._socket is not None:
			raise RuntimeError("Server is already running - socket already exists")
		self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		used_host_name = socket.gethostname() if (self._hostname is None or len(self._hostname) == 0) else self._hostname
		log.info(f"Binding server to {used_host_name}:{self._port}")
		self._socket.bind(( #Bind the socket to the given hostname and port
				used_host_name,
				self._port
		))
		self._connection_listener_thread = threading.Thread(target=self._listen_for_connections)
		self._connection_listener_thread.start()
		self._server_stop_flag.clear()
		# self._listen_for_connections()

	def emit_signal(self, signal_name: str, *args):
		"""Emits a QtCore.Signal to the server

		Args:
			signal_name (str): The signal name
			args*: The arguments to the signal
		"""
		#Print the signal name and args (but max 100 characters)
		log.debug(f"Emitting signal {signal_name} with args: {args if len(str(args)) < 100 else str(args)[:100] + '...'}")

		if self._socket is None:
			log.error("Cannot emit signal - server is not running")
			return

		pickle_data = PickleTransmissionData(
			(PickledDataType.SIGNAL_EMIT, (signal_name, args))
		)
		for client in self._client_dict.values(): #Send all clients the signal
			Transmission.send(
				client.client_socket,
				pickle_data,
				client.client_session_aes_key
			)


	def set_password_hash(self, password_hash : str, invalidate_clients : bool = False):
		"""Sets the password hash to the given value
		if invalidate_clients is True, all clients will be disconnected

		Args:
			password_hash (str): The new password hash
			invalidate_clients (bool, optional): If True, all clients will be disconnected. Defaults to False.
		"""
		if invalidate_clients:
			raise NotImplementedError("Invalidating clients is not yet implemented")
		self._password_hash = password_hash

	@staticmethod
	def get_password_hash(password : str):
		"""Returns the (salted) password hash for the given password

		Args:
			password (str): The password to hash
		"""
		return hashlib.sha512(RunQueueServer._salt + password.encode('utf-8')).hexdigest()


	def _listen_for_connections(self):
		"""To be ran in a separate thread.
		Continually listens for new connections and launches a new thread to authenticate them if found using
		_connection_setup and a new thread.

		#TODO: stopflag/create separate listener class with a qt signal
		"""
		while not self._server_stop_flag.is_set():
			if not self._socket:
				log.warning("Server socket is null - cannot listen for connections - stopping...")
				return
			self._socket.settimeout(DATA_RECEIVE_TIMEOUT) #Set a timeout so we can check if we should stop
			try:
				self._socket.listen(5) #TODO: maybe increase the backlog?
				client, address = self._socket.accept() #TODO: as soon as a client connects, start a new thread to handle
			except (socket.timeout, TimeoutError):
				continue

				#  the new socket as to not block other clients from connecting
			log.info(f"Initial (unauthenticated) connection from {address} has been established - now delegating to \
						a new thread to handle the connection")
			authenticator_thread = threading.Thread(target=self._connection_setup, args=(client, address))
			authenticator_thread.start()



	def _connection_setup(self, client_sock : socket.socket, address : str):
		"""Continuously accept connections and try to initiate a handshake

		The following steps are performed:
		1. Accept a connection from a new client - the client sends its public key (2048 bits)
		2. Return the server public key to the client (encrypted with the client public key) (2048 bits)
		3. Receive the encrypted password from the client & try to decrypt it (512 bits)
		4. If incorrect - stop & send a failure message
		5. If correct, continuously receive data from the client, process it and send the result back

		Args:
			client_sock (socket.socket): The client socket
			address (str): The client address
		"""
		log.info(f"Started authentication process of new client ({address})")
		#Attempt to get client public key
		received = Transmission.receive(client_sock) #First message should be a TransmissionType.pubkey
		client_public_key = None
		if self._is_terminating:
			log.info(f"Server is terminating - could not start connection-setup with {address}")
			return


		if received.transmission_type == TransmissionType.PUB_KEY:
			try:
				pubkey_data = PubKeyTransmissionData.from_transmission_bytes(received.transmission_data)
			except AuthenticationException as auth_exception:
				log.info(f"Error during Authentication of {address}: First transmission from client should be a public\
		 			key, but failed to parse it as such. {auth_exception} - disconnecting...")
				client_sock.close()
				return
			client_public_key = pubkey_data.pubkey
		elif received.transmission_type == TransmissionType.STATE:
			try:
				state_data = StateTransmissionData.from_transmission_bytes(received.transmission_data)
				log.warning(f"Authentication of {address}: Received a state message from {address}: \
					{state_data.state_msg_type.name} - {state_data.state_msg}... But first message should be a public \
					key. Closing connection...")
				client_sock.close()
			except Exception as exception: # pylint: disable=broad-exception-caught
				log.warning(f"First connection should be a public key - failed to parse {address}: {exception} - \
					disconnecting...")
				client_sock.close()
				return
		else:
			log.warning(f"Error during Authentication of {address}: Received a message with TransmissionType: \
		   		{received.transmission_type} - expected TransmissionType.pub_key - disconnecting...")

		if client_public_key is None:
			log.error(f"Error during Authentication of {address}: No public key received in pubkey transmission - \
		 		disconnecting...")
			Transmission.send(
				client_sock,
				StateTransmissionData(
					StateMsgType.ERROR,
					"Failure - no public key received from client - first response message must be a public key"
				)
			)
			return
		log.info(f"Received public key from client {address}: {client_public_key}")

		#Instantiate a rsa key object from the client public key
		client_public_key = RSA.import_key(client_public_key)

		rsa_cipher = PKCS1_OAEP.new(client_public_key)

		#Generate a random AES-session key
		aes_session_key = get_random_bytes(32)

		#Encrypt the AES key with the client public key, and send it to the client
		Transmission.send(
			client_sock,
			AESSessionKeyTransmissionData(
				encrypted_session_key=rsa_cipher.encrypt(aes_session_key) #Encrypt
			)
		)

		log.info(f"Authentication of {address}: session key is {aes_session_key}")

		# ====== FROM NOW ON - ONLY ENCRYPTED MESSAGES SHOULD BE SENT (USING AES) ===== (both parties have the AES key)
		received = Transmission.receive(
			client_sock,
			aes_session_key
		)
		if received.transmission_type != TransmissionType.LOGIN:
			log.error(f"Error during Authentication of {address}: Expected TransmissionType.login - received \
		 		{received.transmission_type.name}({received.transmission_type}) - disconnecting...")
			client_sock.close()
			return
		else:
			log.info(f"Authentication of {address}: Received TransmissionType.login from {address}")
			login_info = LoginTransmissionData.from_transmission_bytes(received.transmission_data)

		hashed_password = self.get_password_hash(login_info.password)
		log.info(f"Authentication of {address} - Received hashed pw {address}: {hashed_password}")
			#TODO: Also implement client-side hashing of the password - send a salt back with the AES-session key?
			# Traffic is encrypted - but server probably shouldn't know the plaintext password attempts.


		#Check if the password hash is correct
		if hashed_password != self._password_hash:
			log.error(f"Error during Authentication of {address}: Invalid password received from {address} - disconnecting...")
			Transmission.send(
				client_sock,
				StateTransmissionData(
					StateMsgType.LOGIN_ERROR,
					"Failure - invalid password hash received from client"
				),
				aes_session_key
			)
			client_sock.close()
			return
		else:
			Transmission.send(
				client_sock,
				StateTransmissionData(
					StateMsgType.LOGIN_ACCEPTED,
					"Success - client authenticated"
				),
				aes_session_key
			)

		ip_list = [client.client_socket.getpeername() for client in self.list_authenticated_clients()]
		log.info(f"Connection with {address} has now been authenticated - starting a new thread to handle the \
	   		client/server interaction. Currently connected clients ({len(ip_list)}): \
	   		{ip_list }")

		#Start a new thread to handle the client/server interaction #TODO: create worker with a qt signal
		client_stop_flag = threading.Event()
		client_stop_flag.clear()
		client_thread = threading.Thread(
			target=self._client_listener,
			args=(
				client_sock,
				address,
				aes_session_key,
				client_stop_flag
			)
		)

		with self._client_dict_lock:
			assert client_sock not in self._client_dict, "Connection cannot already be authenticated/running"
			self._client_dict[client_sock] = ClientData(
				client_socket = client_sock,
				client_public_key = client_public_key,
				client_session_aes_key = aes_session_key,
				client_listening_thread = client_thread,
				client_listening_thread_stop_flag=client_stop_flag
			)
		client_thread.start()

		return #Should end the authentication thread


	def list_authenticated_clients(self) -> typing.List[ClientData]:
		"""Returns a list of all currently connected authenticated clients
		"""
		with self._client_dict_lock:
			return list(self._client_dict.values())


	def _handle_pickled_data(self,
			client : socket.socket,
			client_address : str,
			aes_session_key : bytes,
			pickle_transmission_data: PickleTransmissionData):
		"""
		Handles a pickled object received from a client
		"""
		unpickled_data = pickle_transmission_data.unpickled_data

		assert isinstance(unpickled_data, tuple), "Pickled transmission data should (in this case) always be a tuple of \
			the form (pickledDataType, data)"
		# assert(unpickled_data[0] == pickledDataType.function_call)

		error_msg = None
		if unpickled_data[0] == PickledDataType.METHOD_CALL:
			function_data = unpickled_data[1]
			#Handle a function call
			method_call_id = function_data[0] #So client can identify which response belongs to which call
			function_name = function_data[1]
			args = function_data[2]
			kwargs = function_data[3]
			log.debug(f"Received a function call from a client: {function_name}(self, {args}, {kwargs})")
			try:
				result = getattr(self._run_queue, function_name)(*args, **kwargs)
			except Exception as exception: # pylint: disable=broad-exception-caught
				result = exception
				log.warning(f"Client {client_address} called function {function_name}, which result in \
		 			{type(exception)}: {exception}")

			#Send the result back to the client
			Transmission.send(
				client,
				PickleTransmissionData(
					(PickledDataType.METHOD_RETURN, (method_call_id, result)) #return the call_id and the results
				),
				aes_cypher_key=aes_session_key,
			)
		elif unpickled_data[0] == PickledDataType.SIGNAL_EMIT:
			error_msg = "Received a signal emit from client - this should not be possible - ignoring transmission"
		elif unpickled_data[0] == PickledDataType.METHOD_RETURN:
			error_msg = "Received a function return from client - this should not be possible - ignoring transmission"
		else:
			error_msg = f"Received a pickled object with unknown type: {unpickled_data[0]} - ignoring transmission"

		if error_msg is not None: #Log/send and raise and error if necessary
			Transmission.send(
				client,
				StateTransmissionData(
					StateMsgType.ERROR,
					error_msg
				),
				aes_cypher_key=aes_session_key,
			)
			raise TypeError(error_msg)

	def disconnect_all_clients(self, timeout_seconds : float = 5.0):
		"""
		Attempts to disconnect all clients by sending them a disconnect signal and waiting for them to disconnect.
		Will wait for timeout_seconds seconds for each client to disconnect before giving up and raising a TimeoutError.
		"""
		start_time = time.time()
		with self._client_dict_lock:
			for client_data in self._client_dict.values(): #Flag all clients to stop
				client_data.client_listening_thread_stop_flag.set()

			for client_data in self._client_dict.values(): #Then wait for them to stop
				remaining_time = timeout_seconds - (time.time() - start_time)
				if client_data.client_listening_thread.is_alive(): #Wait for all living client threads to stop
					client_data.client_listening_thread.join(timeout=remaining_time)

				if client_data.client_listening_thread.is_alive(): #If the thread is still alive, it didn't stop in time
					raise TimeoutError(f"Client {client_data.client_socket.getpeername()} did not stop in time...")

			self._client_dict = {}



	def _client_listener(self,
				client : socket.socket,
				client_address : str,
				aes_session_key : bytes,
				client_stop_flag : threading.Event
			):
		"""
		NOTE: this function assumes that the client has already been authenticated and should only be called when this
		is the case. Listens to the given client and handles all incoming requests

		Args:
			client (socket.socket): The client to listen to
			aes_session_key (bytes): The AES session key used to encrypt data between the client and the server
				(required - all data should be authenticated)

		"""
		assert (aes_session_key is not None) and (aes_session_key != AES_EMPTY_KEY), "Session_key can't be null/empty \
			when listening to a client"
		try:
			while not client_stop_flag.isSet(): #TODO: put in a worker so it shuts down automtaically on server close
				try:
					#Receive the transmission data - this should always be succesful as long as the connection is active
					received = Transmission.receive(client, aes_session_key, timeout_seconds=DATA_RECEIVE_TIMEOUT)
					log.info(f"Received transmission from client {client_address} with TransmissionType: \
						{received.transmission_type.name}({received.transmission_type})")

					if received.transmission_type == TransmissionType.PICKLED_OBJECT:
						try:
							pickled_data = PickleTransmissionData.from_transmission_bytes(received.transmission_data)
						except Exception as exception: # pylint: disable=broad-exception-caught
							log.error(f"Failed to unpickle data from client {client_address}: {exception}")
							Transmission.send(
								client,
								StateTransmissionData(
									StateMsgType.ERROR,
									f"Failed to unpickle data from client {client_address}: {exception}"
								)
							)
							continue
						try:
							self._handle_pickled_data(client=client,
								client_address=client_address,
								aes_session_key=aes_session_key,
								pickle_transmission_data=pickled_data
							)
						except Exception as exception: # pylint: disable=broad-exception-caught
							log.error(f"Failed to handle pickled data from client {client_address}: {exception} ")
					elif received.transmission_type == TransmissionType.STATE:
						data = StateTransmissionData.from_transmission_bytes(received.transmission_data)
						log.info(f"State Client : {data.state_msg_type.name} - {data.state_msg}")
					else:
						log.error(f"Received a transmission with TransmissionType: {received.transmission_type.name}\
							({received.transmission_type}) - this should not happen for authenticated clients \
							- ignoring transmission.")
				except TimeoutError:
					pass #Continue
		except Exception as exception: # pylint: disable=broad-exception-caught
			log.error(f"Error during client/server interaction: {exception} - disconnecting client {client_address}")
			with self._client_dict_lock: #Remove the client from the list of authenticated clients
				del self._client_dict[client]
			client.close() #Try to close connection (if not already closed)


def run_example_server(password : str = "password", port : int = 5454, log_level : int = logging.INFO):
	"""
	Runs an example-instance of the server, using the example_target_function from 
	configurun/examples/example_target_function.py and the passed password as well as the default
	workspace path (~/Configurun-Server)

	Args:
		password (str, optional): The password to connect to the server. Defaults to "password".
	"""
	#pylint: disable=import-outside-toplevel
	from configurun.server.create_server import run_server
	import tempfile
	from configurun.examples.example_target_function import example_target_function
	tempdir = tempfile.gettempdir()
	workspace_path = os.path.join(tempdir, "Configurun", "Configurun-Server-Example")

	run_server(
		target_function=example_target_function,
		workspace_path=workspace_path,
		password=password,
		port=port,
		log_level=log_level
	)


if __name__ == "__main__":
	run_example_server(log_level=logging.DEBUG)
