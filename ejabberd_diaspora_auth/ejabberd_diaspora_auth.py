#!/usr/bin/python3

import sys
import os
import re
import logging
import struct
import bcrypt
import yaml
import MySQLdb

re_pepper = re.compile(r'.*config.pepper = "([a-z0-9]*)')

# Setup the logging
sys.stderr = open('/var/log/ejabberd/diaspora_auth_err.log', 'a')
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename='/var/log/ejabberd/diaspora_auth.log',
                    filemode='a')

logging.debug("Python version: %s"%sys.version)

def parse_yaml_file(filename):
	result = yaml.load(open(filename))
	return result

def get_pepper(filename):
	for line in open(filename).readlines():
		if line.find('config.pepper') != -1:
			if re_pepper.match(line):
				pepper = (re_pepper.findall(line))[0]
				return pepper
			return line

if os.environ.get('DIASPORA_DIR'):
	DIASPORA_DIR = os.environ.get('DIASPORA_DIR')
else:
    DIASPORA_DIR = "/home/vrije-mens/diaspora"

filename = os.path.join(DIASPORA_DIR, "config/database.yml")
db_config = parse_yaml_file(filename)['production']
filename = os.path.join(DIASPORA_DIR, "config/initializers/devise.rb")
pepper = get_pepper(filename)

try:
	db_password = db_config['password']
except:
	db_password = db_config['mysql']['password']
try:
	db_host = db_config['host']
except:
	db_host = db_config['mysql']['host']
try:    
	db_user = db_config['username']
except:
	db_user = db_config['mysql']['username']
try:    
	db_port = db_config['port']
except:
	db_port = db_config['mysql']['port']    
    
db_dbname = 'diaspora_production'

# start mysql
MySQLdb.paramstyle = 'pyformat'

try:
	database=MySQLdb.connect(db_host, db_user, db_password, db_dbname)
	cur = database.cursor()
except:
	logging.error("Unable to initialize database, check settings!")
	time.sleep(10)
	sys.exit(1)

def close_db():
	database.close()

logging.info('extauth script started, waiting for ejabberd requests')

class EjabberdInputError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

########################################################################
#Declarations
########################################################################

def get_user(cur, username):
	cur.execute("SELECT username, encrypted_password FROM users WHERE username =%s;", (username,))
	user = cur.fetchone()    
	return user

def valid_user(cur, username):
	cur.execute("SELECT count(username) FROM users WHERE username =%s;", (username,))
	result = cur.fetchone()
	if result[0]==1:
		return True
	else:
		return False
    
def auth_user(cur, username, password):
	user = get_user(cur, username)
	logging.debug('auth_user %s'%user[0])
	password_txt = '%s%s' % (password, pepper)
	encrypted_password = user[1].encode('utf8')
	result = bcrypt.checkpw(password_txt.encode('utf-8'), encrypted_password)
	password_hash = bcrypt.hashpw(password_txt.encode('utf-8'), bcrypt.gensalt())
	logging.debug("Auth = %s"%result)
	return result

def from_ejabberd():
	logging.debug("trying to read 2 bytes from ejabberd:")
	input_length = sys.stdin.read(2)
	if len(input_length) is not 2:
		logging.debug("ejabberd sent us wrong things!")
		raise EjabberdInputError('Wrong input from ejabberd!')
	logging.debug('got 2 bytes via stdin: %s'%input_length)
	(size,) = struct.unpack('>h', str.encode(input_length))
	logging.debug('size of data: %i'%size)
	income = sys.stdin.read(size).split(':', 3)
	logging.debug("income: %s"%income)
	return income

def to_ejabberd(bool):
	logging.debug("to_ejabberd %s beg" % bool)
	answer = 0
	if bool:
		answer = 1
	token = struct.pack('>hh', 2, answer)
	sys.stdout.write(token.decode())
	sys.stdout.flush()
	logging.debug("to_ejabebrd %s end" % bool)

def auth(username, server, password):
	return auth_user(cur, username, password)

def isuser(username, server):
	return valid_user(cur, username)

def setpass(username, server, password):    
	return False

try:
	while True:
		data = from_ejabberd()
		success = False
		logging.debug("incoming data: %s"%data)
		if data[0] == "auth":
			logging.debug("start auth")
			success = auth(data[1], data[2], data[3])
			logging.debug("end auth")
		elif data[0] == "isuser":
			success = isuser(data[1], data[2])
		elif data[0] == "setpass":
			success = setpass(data[1], data[2], data[3])
		logging.debug("send to ejabberd %s" % success)
		to_ejabberd(success)
		logging.debug("sent to ejabberd %s" % success)
except Exception:
	logging.error('problem happened', exc_info=True)

