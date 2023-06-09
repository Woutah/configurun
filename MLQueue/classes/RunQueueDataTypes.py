"""
Describes all the data types used for communication between the client and the server
Examples:
	- Transmission: A transmission containing the transmission type and the transmission data
	- TransmissionType: The type of transmission (e.g. public key, login, ...), how to handle transmission data
	- TransmissionData: The data of a transmission (e.g. the public key, the login password, ...)

	- clientData: The data of a client (e.g. the client socket, the client public key, the client session key, ...)
	- serverData: The data of a server (e.g. the server socket, the server private key, ...)

"""

import enum
from dataclasses import dataclass
from abc import abstractmethod
import pickle
import socket
from ctypes import c_uint32
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes


RSA_KEY_SIZE_BITS = 2048 #The size of the key used for encryption/decryption
PASSWORD_HASH_SIZE = 512 #The size of the password hash in bytes
AES_KEY_SIZE = 32 #The size of the used AES key in bytes
AES_EMPTY_KEY = b"\x00"*16 #16 bytes of "0" - not used when not encrypted


class TransmissionType(enum.IntEnum):
	"""
	A transmission type - communication between client and server is done by specifying the transmission type,
	followed by the transmission data. The transmission type specifies what kind of data is being sent and how the 
	client should handle this data. Also see the ```Transmission``` class.
	"""
	#=========== (Always) Unencrypted transmissions ===========
	pub_key = 0 #Sending of public key - 2048 

	#=========== Sometimes encrypted transmissions ===========
	state = enum.auto() #A raw state transmission consisting of this unsigned integer, followed the state unsigned 
		#integer, followed by a string of size 2048(bits)
	
	#=========== Always Encrypted transmissions ===========
	session_key = enum.auto() #Sending of session key - 256
	login = enum.auto() #Sending of password
	pickled_object = enum.auto() #Sending of data

class stateMsgType(enum.Enum):
	"""
	If transmissiontype is state, then this enum specifies the type of state message
	"""
	error = 0 #A general error message has been sent
	login_error = enum.auto() # a loging error has occured
	login_accepted = enum.auto() #The login has been accepted
	general_msg = enum.auto() #A general message has been sent


class pickledDataType(enum.Enum):
	"""
	If transmissiontype is pickled_object, then this enum specifies the type of pickled data.
	Determines what is done with a TransmissionType.pickled_object transmission
	"""
	method_call = 0 #The pickled data is a function call
	method_return = enum.auto() #The pickled data is a function result
	signal_emit = enum.auto() #The pickled data is a signal emit

	def __eq__(self, __value: 'pickledDataType') -> bool:
		"""Overload the default __eq__ function to also work with pickled/unpickled data, don't compare the enum 
		hashes to each other, instead compare the name and value of the enum
		"""
		return (type(self).__qualname__ == type(__value).__qualname__) \
			and (self.name == __value.name and self.value == __value.value)



@dataclass
class TransmissionData():
	"""
	Base class for transmissiondata. 
	All transmission data should inherit from this class and implement the abstract methods. 
	"""
	@staticmethod
	@abstractmethod
	def from_transmission_bytes(transmission_data : bytes) -> 'PubKeyTransmissionData':
		raise NotImplementedError("Abstract method from_transmission_data should be implemented by subclass")
	
	@abstractmethod
	def to_transmission_bytes(self) -> bytes:
		raise NotImplementedError("Abstract method to_transmission_data should be implemented by subclass")
	
	@property
	@abstractmethod
	def TRANSMISSION_TYPE(self) -> TransmissionType:
		raise NotImplementedError("Abstract property transmission_type should be implemented by subclass")
	

@dataclass
class PickleTransmissionData(TransmissionData):
	"""
	A transmission containing a pickled object. Is used as a general-purpose transmission type
	to allow for the transmission of arbitrary objects. 
	NOTE: this transmission type should ALWAYS be encrypted using AES, and should only be allowed 
	after authentication as it allows for arbitrary code execution on the server-side. 
	"""

	unpickled_data : object #The unpickled data

	@staticmethod
	def from_transmission_bytes(transmission_data : bytes) -> 'PickleTransmissionData':
		unpickled_data = pickle.loads(transmission_data)
		return PickleTransmissionData(unpickled_data)
	
	def to_transmission_bytes(self) -> bytes:
		return pickle.dumps(self.unpickled_data)
	
	@property
	def TRANSMISSION_TYPE(self) -> TransmissionType:
		return TransmissionType.pickled_object

@dataclass
class PubKeyTransmissionData(TransmissionData):
	"""
	A transmission that contains the public key of the server
	"""
	pubkey : bytes #The public key of the server
	
	@property 
	def TRANSMISSION_TYPE(self) -> TransmissionType:
		return TransmissionType.pub_key
	
	@staticmethod
	def from_transmission_bytes(transmission_data : bytes) -> 'PubKeyTransmissionData':
		"""Receives a pubkey transmission from the given socket (assumes that the <transmission_type> has already been
		  received which resulted in PubkeyTransmission)
		Args:
			transmission_data (bytes): The data-part of the transmission from which to create the pubkey
		Returns:
			PubkeyTransmission: A pubkey transmission object
		"""
		#Receive the public key
		# assert(len(transmission_data) == RSA_KEY_SIZE_BITS/8) #Should be exactly the size of the public key
		pubkey = transmission_data
		return PubKeyTransmissionData(pubkey)

	def to_transmission_bytes(self) -> bytes:
		"""
		Returns the transmission data of a pubkey transmission
		NOTE: this can never be encrypted as the client does not have the public key of the server yet
		"""
		data=bytearray()
		data.extend(self.pubkey) #Public key
		return data

@dataclass
class LoginTransmissionData(TransmissionData):
	"""A login transmission - contains a password. 
	NOTE: SHOULD ALWAYS BE ENCRYPTED WITH AES - as it contains the password hash
	TODO: also hash the password on the client side to prevent server from knowing the password
	"""
	password : str #The password hash of the user

	@property
	def TRANSMISSION_TYPE(self) -> TransmissionType:
		return TransmissionType.login
	
	@staticmethod
	def from_transmission_bytes(transmission_data: bytes) -> 'LoginTransmissionData':
		# assert(len(transmission_data) == PASSWORD_HASH_SIZE)
		return LoginTransmissionData(
			password=transmission_data.decode('utf-8') #Decode bytes to string
		)
	
	def to_transmission_bytes(self) -> bytes:
		"""Returns the transmission data of a pubkey transmission
		"""
		data=bytearray()
		data.extend(self.password.encode('utf-8')) #Encode string to bytes
		return data

@dataclass
class AESSessionKeyTransmissionData(TransmissionData):
	"""A transmission that contains the session key encrypted with the public key of the server
	"""
	encrypted_session_key : bytes #The encrypted session key

	@property
	def TRANSMISSION_TYPE(self) -> TransmissionType:
		return TransmissionType.session_key
	
	@staticmethod
	def from_transmission_bytes(transmission_data: bytes) -> 'AESSessionKeyTransmissionData':
		assert(len(transmission_data) == RSA_KEY_SIZE_BITS/8) #Should be exactly the size of the public key
		return AESSessionKeyTransmissionData(
			encrypted_session_key=transmission_data
		)
	
	def to_transmission_bytes(self) -> bytes:
		"""Returns the transmission data of a pubkey transmission
		"""
		data=bytearray()
		data.extend(self.encrypted_session_key)
		return data
	
@dataclass
class StateTransmissionData(TransmissionData):
	TRANSMISSION_TYPE = TransmissionType.state # type: ignore
	state_msg_type : stateMsgType #The current state of the transmission
	state_msg : str #A message describing the current state of the transmission -> should be max 2048 bytes/characters
	
	@property 
	def TRANSMISSION_TYPE(self) -> TransmissionType:
		return TransmissionType.state
	
	@staticmethod
	def from_transmission_bytes(transmission_data : bytes) -> 'StateTransmissionData':
		state_msg_type = stateMsgType(c_uint32.from_buffer_copy(transmission_data[:4]).value)
		state_msg = transmission_data[4:].decode('utf-8')
		return StateTransmissionData(state_msg_type, state_msg)

	def to_transmission_bytes(self) -> bytes:
		"""Converts StateTransmission to a byte array used for sending"""
		data = bytearray()
		data.extend(c_uint32(self.state_msg_type.value)) # type: ignore
		data.extend(self.state_msg.encode('utf-8'))
		return data


@dataclass
class Transmission():
	transmission_size : int #The size of the transmission (excluding this field) - determined how many bytes to receive
	transmission_type : TransmissionType #The type of the transmission
	transmission_data : bytes #The raw data of the transmission - defined by the subclass


	@staticmethod
	def receive(socket : socket.socket, aes_cipher_key : bytes | None  = None) -> 'Transmission': #TODO: timeout
		"""Receives the data of the transmission from the given socket
		Args:
			socket (socket.socket): The socket to receive the transmission from
			aes_cipher_key (bytes): The aes-cipher-key used to decrypt the data - if not provided - the data is assumed
			 to be unencrypted (e.g. when receiving a public key)
		Returns:
			TransmissionType: The type of the transmission
			bytes: The raw data of the transmission
		"""
		#Receive the transmission data
		transmission_size = socket.recv(4)
		transmission_size = c_uint32.from_buffer_copy(transmission_size).value #Read in uint32, convert to python type

		aes_nonce = socket.recv(16) #Receive the nonce used for AES encryption

		data = socket.recv(transmission_size)

		if aes_cipher_key is not None:
			aes_cipher = AES.new(aes_cipher_key, AES.MODE_EAX, nonce=aes_nonce)
			data = aes_cipher.decrypt(data)


		newTransmission = Transmission(
			transmission_size = transmission_size,
			transmission_type = TransmissionType(
				c_uint32.from_buffer_copy(data[:4]).value #First 4 bytes are the transmission type
			), 
			transmission_data = data[4:]
		)
		return newTransmission

	@staticmethod
	def send(socket : socket.socket, transmission_data : TransmissionData, aes_cypher_key : bytes | None  = None):
		"""Sends the data of the transmission to the given socket

		Args:
			socket (socket.socket): The socket to send the transmission to
			transmission_data (TransmissionType): The type of the transmission
			aes_cipher_key (any): The cipher key used for aes encryption - note that some types of transmissions
				should always be encrypted (e.g. login, session key, ...) and some should never be encrypted 
				(e.g. public key), some assertions are made.
		"""
		bytes_data = transmission_data.to_transmission_bytes()

		if aes_cypher_key is None:
			#Allow only the following transmission types to be unencrypted:
			assert(type(transmission_data) == PubKeyTransmissionData or 
	  				(type(transmission_data) == StateTransmissionData) or #Should also be encrypted with AES when auth. 
					(type(transmission_data) == AESSessionKeyTransmissionData) #Session token is sha-key-encrypted
				), f"Transmission type {transmission_data.TRANSMISSION_TYPE} should always be encrypted with AES when \
					  transmitting, but no AES key was provided"

		cur_transmission = Transmission(
			transmission_size = len(bytes_data) + 4,
			transmission_type = transmission_data.TRANSMISSION_TYPE,
			transmission_data = bytes_data
		)
		cur_transmission._send(socket, aes_cypher_key)


	def _send(self, socket : socket.socket, aes_cypher_key : bytes | None  = None):
		"""Sends the transmission to the given socket
		Args:
			socket (socket.socket): The socket to send the transmission to
			aes_cipher (any): The AES cipher used to encrypt the data - if not provided - the data is assumed to be unencrypted (e.g. when sending a public key )
		"""
		packet = bytearray()
		packet.extend(c_uint32(self.transmission_size))  # type: ignore

		data = bytearray()
		data.extend(c_uint32(self.transmission_type.value)) # type: ignore
		data.extend(self.transmission_data)

		nonce =  AES_EMPTY_KEY #16 bytes of "0" - not used when not encrypted
		if aes_cypher_key is not None:
			while(nonce == AES_EMPTY_KEY): #Generate a new nonce if it is all 0's (not allowed) -> is VERY unlikely to happen though... but just in case.
				nonce = get_random_bytes(16)

			aes_cipher = AES.new(aes_cypher_key, AES.MODE_EAX, nonce=nonce)
			data = aes_cipher.encrypt(data)

		packet.extend(nonce) #Add the nonce to the packet
		packet.extend(data)

		socket.sendall(packet) #Packet: 4bytes transmission_size, 16 bytes nonce, transmission_data



@dataclass
class clientData():
	client_socket : socket.socket
	client_public_key : RSA.RsaKey #TODO: not really necceasry? 
	client_session_aes_key : bytes #The session key used to encrypt data between the client and the server


