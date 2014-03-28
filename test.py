from datetime import datetime, timedelta
import cgi
import urllib, urllib2
import json
import logging

from google.appengine.api import taskqueue
from google.appengine.api import users
from google.appengine.ext import ndb
#from django.core.cache import cache
#from django.utils import importlib

import webapp2

class GCMException(Exception): pass
class GCMMalformedJsonException(GCMException): pass
class GCMConnectionException(GCMException): pass
class GCMAuthenticationException(GCMException): pass
class GCMTooManyRegIdsException(GCMException): pass
class GCMNoCollapseKeyException(GCMException): pass
class GCMInvalidTtlException(GCMException): pass

# Exceptions from Google responses
class GCMMissingRegistrationException(GCMException): pass
class GCMMismatchSenderIdException(GCMException): pass
class GCMNotRegisteredException(GCMException): pass
class GCMMessageTooBigException(GCMException): pass
class GCMInvalidRegistrationException(GCMException): pass
class GCMUnavailableException(GCMException): pass

REGUSERSECT = 'reg_user_section'
GCM_URL = 'https://android.googleapis.com/gcm/send'
GCM_API_KEY = 'AIzaSyAfWnSGUuEqr8V9kQEw5SgyxOej36REwcE'
GCM_QUEUE_NAME = 'gcm-retries'
GCM_QUEUE_CALLBACK_URL = '/resendGCM'
RETRY_AFTER = 'retry_after'
TOTAL_ERRORS = 'total_errors'
TOTAL_MESSAGES = 'total_messages'

def reg_user_key(section_name=REGUSERSECT):
    return ndb.Key('Section', section_name)

class RegisteredUser(ndb.Model):
	"""Models an individual RegisteredUser entry with name, phoneNumber, email, and password."""
	name = ndb.StringProperty(indexed=True)
	phoneNumber = ndb.StringProperty(indexed=False)
	email = ndb.StringProperty(indexed=True)
	password = ndb.StringProperty(indexed=False)
	reg_id = ndb.StringProperty()
	#pref_cities
	#music
	#
                
##################################
class Login(webapp2.RequestHandler):

	def get(self):
		section_name = REGUSERSECT

		#Check if user actually exists
		users_query = RegisteredUser.query(
			ancestor=reg_user_key(section_name))
		users = users_query.filter(RegisteredUser.email == self.request.get('email')).get() 	#should only return 1 user
		#users = RegisteredUser.all().filter('email',self.request.get('email')).get()
		
		if users and users.email == self.request.get('email'):							#if email is a match
			if users.password == self.request.get('password'):				#if password is a match
				self.response.out.write('correct-' + users.name)
				logging.info("User: \""+users.email+"\" Successfully logged in")
			else:															
				self.response.out.write('incorrect') #CHANGE back to INCORRECT
				logging.info("User: \""+users.email+"\" Unsuccessfully logged in (Password Incorrect)")
		else: 															
			self.response.out.write('incorrect') #CHANGE back to INCORRECT
			logging.info("User: \""+self.request.get('email')+"\" Unsuccessfully logged in (No Known User)")
				
###################################				
class RegUsersSection(webapp2.RequestHandler):

	def post(self):
	
		section_name = REGUSERSECT
		regsUser = RegisteredUser(parent=reg_user_key(section_name))
        
        #Check if user already exists
		users_query = RegisteredUser.query(
			ancestor=reg_user_key(section_name))
		users = users_query.filter(RegisteredUser.email == self.request.get('email')).get()
		#users = users_query.filter("email =", self.request.get('email'))
		#users = RegisteredUser.all().filter('email',self.request.get('email')).get()
		if users:    ##user exists
			self.response.out.write('User Already exists')
			logging.info("User: \""+users.name+"\" already exists")
		else:                  ##add user to section
			regsUser.name = self.request.get('name')
			regsUser.email = self.request.get('email')
			regsUser.password = self.request.get('password')
			regsUser.phoneNumber = self.request.get('phoneNumber')
			regsUser.reg_id = None
			logging.info("User: \""+regsUser.email+"\" Successfully registered")
			regsUser.put()
			self.response.out.write('User Registration Successful')

##################################
class UserInfo(webapp2.RequestHandler):

	def get(self):
		section_name = REGUSERSECT

		#find user that was selected
		users_query = RegisteredUser.query(
			ancestor=reg_user_key(section_name))
		users = users_query.filter(RegisteredUser.email == self.request.get('email')).get() 	#should only return 1 user

		if users and users.email == self.request.get('email'):	#if email is a match
			self.response.out.write(users.name + '-' + users.phoneNumber + '-' + users.email)
##################################
REGSEARCHSECT = 'ride_search_section'

def ride_offer_key(section_name=REGSEARCHSECT):
	return ndb.Key('Section', section_name)

class RideRequest(ndb.Model):
	name = ndb.StringProperty(indexed=True);
	email = ndb.StringProperty(indexed=True);
	location = ndb.StringProperty(indexed=True)
	destination = ndb.StringProperty(indexed=True)
	month = ndb.StringProperty(indexed=True)
	day = ndb.StringProperty(indexed=True)
	year = ndb.StringProperty(indexed=True)
	hours = ndb.StringProperty(indexed=True)
	minutes = ndb.StringProperty(indexed=True)

class SearchRider(webapp2.RequestHandler):

	def get(self):
		section_name = REGSEARCHSECT

		users_query = RideRequest.query(
			ancestor=ride_offer_key(section_name)).order(-RideRequest.name)
		users = users_query.filter(RideRequest.location == self.request.get('location')).filter(RideRequest.destination == self.request.get('destination')).filter(RideRequest.month == self.request.get('month')).filter(RideRequest.day == self.request.get('day')).filter(RideRequest.year == self.request.get('year')).filter(RideRequest.hours == self.request.get('from_hr')).filter(RideRequest.minutes == self.request.get('from_min')).filter(RideRequest.hours == self.request.get('to_hr')).filter(RideRequest.minutes == self.request.get('to_min'))

		if users:					
			for user in users:		#for all matches, add to response.out
				self.response.out.write(user.name + '-' + user.email + '-')     #in android class keep track of name's position in list to user here	
		else:
			self.response.out.write('No matches')
        
##############################
class RequestRide(webapp2.RequestHandler):

	def post(self):
	
		section_name = REGSEARCHSECT
		
		#LATER::::disallow users to input same request multiple times..
		rider = RideRequest(parent=ride_offer_key(section_name))
		rider.name = self.request.get('name')
		rider.email = self.request.get('email')
		rider.location = self.request.get('location')
		rider.destination = self.request.get('destination')
		rider.hours = self.request.get('hour'); 
		rider.minutes = self.request.get('minute')
		rider.month = self.request.get('month')
		rider.day = self.request.get('day')
		rider.year = self.request.get('year')
		rider.put()
		self.response.out.write('okay')
#######################################
DRIVERSEARCHSECT = 'offer_search_section'

def ride_offer_key(section_name=DRIVERSEARCHSECT):
	return ndb.Key('Section', section_name)

class RideOffer(ndb.Model):
	name = ndb.StringProperty(indexed=True);
	email = ndb.StringProperty(indexed=True);
	location = ndb.StringProperty(indexed=True)
	destination = ndb.StringProperty(indexed=True)
	month = ndb.StringProperty(indexed=True)
	day = ndb.StringProperty(indexed=True)
	year = ndb.StringProperty(indexed=True)
	hours = ndb.StringProperty(indexed=True)
	minutes = ndb.StringProperty(indexed=True)
	seats = ndb.StringProperty(indexed=True)
	seat_cost = ndb.StringProperty(indexed=True)
#######################################	
class SearchDriver(webapp2.RequestHandler):

	def get(self):
		section_name = DRIVERSEARCHSECT

		users_query = RideOffer.query(
			ancestor=ride_offer_key(section_name)).order(-RideOffer.name)
		users = users_query.filter(RideOffer.location == self.request.get('location')).filter(RideOffer.destination == self.request.get('destination')).filter(RideOffer.month == self.request.get('month')).filter(RideOffer.day == self.request.get('day')).filter(RideOffer.year == self.request.get('year')).filter(RideOffer.hours == self.request.get('from_hr')).filter(RideOffer.minutes == self.request.get('from_min')).filter(RideOffer.hours == self.request.get('to_hr')).filter(RideOffer.minutes == self.request.get('to_min'))

		if users:					
			for user in users:		#for all matches, add to response.out
				self.response.out.write(user.name + '-' + user.email + '-')     
				
		else:
			self.response.out.write('No matches')
#######################################
class OfferRide(webapp2.RequestHandler):

	def post(self):
	
		section_name = DRIVERSEARCHSECT
		
		#LATER::::disallow users to input same request multiple times..
		driver = RideOffer(parent=ride_offer_key(section_name))
		driver.name = self.request.get('name')
		driver.email = self.request.get('email')
		driver.location = self.request.get('location')
		driver.destination = self.request.get('destination')
		driver.hours = self.request.get('hour'); 
		driver.minutes = self.request.get('minute')
		driver.month = self.request.get('month')
		driver.day = self.request.get('day')
		driver.year = self.request.get('year')
		driver.seats = self.request.get('seats')
		driver.seat_cost = self.request.get('seat_cost')
		driver.put()
		self.response.out.write('okay')
#######################################		
class TestRide(webapp2.RequestHandler):
	def get(self):
		section_name = REGUSERSECT

		#Check if user actually exists
		users_query = RegisteredUser.query(
			ancestor=reg_user_key(section_name))
		#users = users_query.filter('email =', self.request.get('email'))
		users = users_query.filter(RegisteredUser.email == self.request.get('email')).get()
		if users:
			self.response.write(users.email)
		else:
			self.response.write("No File on Email: " + self.request.get('email'))
		#if users.email == self.request.get('email'):							#if email is a match
		#	if users.password == self.request.get('password'):				#if password is a match
		#		self.response.write('correct-' + user.name)
		#	else:															
		#		self.response.write('correct-') #CHANGE back to INCORRECT
                
		#else: 																#if email is not a match 
		#	self.response.out.write('correct-')
#######################################
class GCMResend(webapp2.RequestHandler):
	def post(self):
		reg_ids = self.request.get('registration_id')
		if not reg_ids:
			logging.error('ERROR: GCM resend request does not contain any registration IDs')
			return
		data = self.request.get('data')
		if not data:
			logging.error('ERROR: GCM resend request does not have any data')
			return
		collapse_key = self.request.get('collapse_key')
		if not collapse_key:
			gcm_message = GCMMessage(reg_ids,data)
		else:
			gcm_message = GCMMessage(reg_ids,data,collapse_key)
		GCMConnection.notify_device(gcm_message)
#######################################
class GCMMessage:
	reg_ids = None
	data = None
	collapse_key = None
	delay_while_idle = None
	time_to_live = None
	
	def __init__(self,reg_ids,data,collapse_key=None,delay_while_idle=None,time_to_live=None):
		if isinstance(data,list):
			self.reg_ids = reg_ids
		else:
			self.reg_ids = [reg_ids]
		self.data = data
		self.collapse_key = collapse_key
		self.delay_while_idle = delay_while_idle
		self.time_to_live = time_to_live
	def __unicode__(self):
		return "%s:%s:%s:%s:%s" % (repr(self.reg_ids),repr(self.data),repr(self.collapse_key),repr(self.delay_while_idle),repr(self.time_to_live))
	def json_string(self):
		if not self.reg_ids or not isinstance(self.reg_ids,list):
			logging.error('ERROR: GCMMessage generate_json_string error. Invalid Registration IDs: ' + repr(self))
			raise Exception('GCMMessage generate_json_string error. Invalid Registration IDs')
		payload = {}
		payload['registration_ids'] = self.reg_ids
		
		if isinstance(self.data,dict):
			payload['data'] = self.data
		else:
			payload['data'] = {'data': self.data}
		if self.collapse_key:
			payload['collapse_key'] = self.collapse_key
		if self.delay_while_idle:
			payload['delay_while_idle'] = self.delay_while_idle
		if self.time_to_live:
			payload['time_to_live'] = self.time_to_live
		json_str = json.dumps(payload)
		return json_str
#######################################
class GCMConnection:
	#Call this to send a push notification to device(s)
	def notify_device(self,message,deferred=False):
		#self._incr_memcached(TOTAL_MESSAGES,1)
		#self._submit_message(message,deferred=deferred)
		self._send_request(message)
		
	def delete_bad_reg_id(self,bad_reg_id):##################### UPDATE BEFORE USING
		logging.info('delete_bad_reg_id(): '+ repr(bad_reg_id))
		#find user with same reg_id and update/(or) delete user
	
	def update_reg_id(self,old_reg_id,new_reg_id): ############# UPDATE BEFORE USING
		logging.info('update_reg_id(): ' + repr((old_reg_id,new_reg_id)))
		#find user with same old_reg_id and update with new_reg_id
	
	
	def _gcm_connection_memcache_key(self,variable_name):
		return 'GCMConnection:'+variable_name
		
	#def _get_memcached(self,variable_name):
	#	memcache_key = self._gcm_connection_memcache_key(variable_name)
	#	return cache.get(memcache_key)
		
	#def _incr_memcached(self,variable_name,increment):
	#	memcache_key = self._gcm_connection_memcache_key(variable_name)
	#	try:
	#		return cache.incr(memcache_key, increment)
	#	except ValueError:
	#		return cache.set(memcache_key, increment)
	
	#Add message to queue
	def _requeue_message(self,message):
		taskqueue.add(queue_name=GCM_QUEUE_NAME,url=GCM_QUEUE_CALLBACK_URL,
						params={'reg_ids': message.reg_ids,
								'collapse_key': message.collapse_key,
								'data': message.data})
	
	# If send message now or add it to the queue
	#def _submit_message(self,message):
	#		self._send_request(message)
	
	# Try sending message now
	def _send_request(self,message):
		if message.reg_ids == None or messsage.data == None:
			logging.error('Message must contain Registration IDs and Data/notification')
			return False
		retry_after = self._get_memcached(RETRY_AFTER)
		#check for resend_after
		if retry_after != None and retry_after > datetime.now():
			logging.warning('Retry_After: '+repr(retry_after) + ",requeueing message: "+repr(message))
			self._requeue_message(message)
			return
		#Build request
		headers = {
				'Authorization': 'key=' + GCM_API_KEY,
				'Content-Type:': 'application/json'
		}
		gcm_post_json_str = ''
		try:
			gcm_post_json_str = message.json_string()
		except:
			logging.exception('Error generating json string for message: '+repr(message))
			return
		logging.info('Sending gcm_post_body: '+repr(gcm_post_json_str))
		request = urllib2.Request(GCM_URL,gcm_post_json_str,headers)
		
		#post
		try:
			response = urllib2.urlopen(request)
			resp_json_str = resp.read()
			resp_json = json.loads(resp_json_str)
			logging.info('_send_request() resp_json: '+repr(resp_json))
			
			failure = resp_json['failure']
			canonical_ids = resp_json['canonical_ids']
			results = resp_json['results']
			
			#if the value of failure and canonical_ids is 0, its not necessary to parse the remainder of the response
			if failure == 0 and canonical_ids == 0:
				return #Success, finised
			else:
				# Process result messages for each token (result index matches original token index from message) 	
				result_index = 0
				for result in results:
					if 'message_id' in result and 'registration_id' in result:
						#update device reg_id
						try:
							old_reg_id = message.reg_ids[result_index]
							new_reg_id = result['registration_id']
							self.update_token(old_reg_id,new_reg_id)
						except:
							logging.exception('Error updating device token')
						return
					elif 'error' in result:
						#Handle GCM error
						error_msg = result.get('error')
						try:
							reg_id = message.reg_ids[result_index]
							self._on_error(reg_id,error_msg,message)
						except:
							logging.exception('Error handling GCM error: ' + repr(error_msg))
						return
					result_index += 1
		except urllib2.HTTPError, e:
			#self._incr_memcached(TOTAL_ERRORS,1)
			if e.code == 400:
				logging.error('400: Invalid GCM JSON message: '+repr(gcm_post_json_str))
			elif e.code == 401:
				logging.error('401: Error authenticating with GCM. Retrying message. Might need to fix auth key')
				self._requeue_message(message)
			elif e.code == 500:
				logging.error('500: Internal Error in GCM Server while trying to send message: '+repr(gcm_post_json_str))
			elif e.code == 503:
				retry_seconds = int(resp.headers.get('Retry-After')) or 10
				logging.error('503: Throttled. Retry after delay. Requeuing message. Delay in ' + str(retry_seconds)+ ' seconds')
				retry_timestamp = datetime.now() + timedelta(seconds=retry_seconds)
				#self._set_memcached(RETRY_AFTER, retry_timestamp)
				self.requeue_message(message)
			else:
				logging.exception('Unexpected HTTPError ('+str(e.code)+ "): "+e.msg+" "+e.read())
	def _on_error(self,reg_id,error_msg,message):
		self._incr_memcached(TOTAL_ERRORS,1)
		
		if error_msg == "MissingRegistration":
			logging.error('ERROR: GCM message sent without registration ID')
			
		elif error_msg == "InvalidRegistration":
			logging.info('Registration ID (' + repr(reg_id)+ ') is Invalid')
			self.delete_bad_reg_id(reg_id)
			
		elif error_msg == "MismatchSenderId":
			logging.error('ERROR: Registration ID is tied to a different sender ID: ' + repr(reg_id))
			self.delete_bad_reg_id(reg_id)
			
		elif error_msg == "NotRegistered":
			logging.info('Registration ID ('+ repr(reg_id)+') Not Registered')
			self.delete_bad_reg_id(reg_id)
		
		elif error_msg == "MessageTooBig":
			logging.error('ERROR: GCM Message too large (max 4096 bytes). ')
			
		elif error_msg == "InvalidTtl":
			logging.error("ERROR: GCM Time to Live field must be an integer representing a deruation in seconds between 0 and 2,419,200 (4 weeks)")
			
		elif error_msg == "Unavaliable":
			retry_seconds = 10
			logging.error('ERROR: GCM Unavaliable. Retry after delay. Requeuing message. Delay in ' + str(retry_seconds)+ ' seconds')
			retry_timestamp = datetime.now() + timedelta(seconds=retry_seconds)
			self._set_memcached(RETRY_AFTER,retry_timestamp)
			self._requeue_message(message)
		
		elif error_msg == "internalServerError":
			logging.error('ERROR: Internal error in the GCM Server while trying to send message: ' + repr(message))
		
		else:
			logging.error('Unknown error: %s for Registration ID: %s' % (repr(error_msg), repr(reg_id)))
#######################################
class GCMRegister(webapp2.RequestHandler):
	def post(self):
		reg_ids = self.request.get('registration_id')
		#user = self.request.get('email')
		section_name = REGUSERSECT
		#Check if user actually exists
		users_query = RegisteredUser.query(
			ancestor=reg_user_key(section_name))
		#users = users_query.filter('email =', self.request.get('email'))
		users = users_query.filter(RegisteredUser.email == self.request.get('email')).get()
		if users:
			users.reg_id = self.request.get('registration_id')
			logging.info("User: "+users.email+" registered ID "+reg_ids)
			self.response.out.write('registered')
		else:
			self.response.out.write(self.request.get('email')+' Account not found')
			logging.info("User: "+self.request.get('email')+" registering ID unsuccessful, Account not found")
class GCMUnregister(webapp2.RequestHandler):
	def post(self):
		section_name = REGUSERSECT
		regsUser = RegisteredUser(parent=reg_user_key(section_name))
		#Check if user actually exists
		users_query = RegisteredUser.query(
			ancestor=reg_user_key(section_name))
		#users = users_query.filter('email =', self.request.get('email'))
		users = users_query.filter(RegisteredUser.email == self.request.get('email')).get()
		if users:
			regsUser.reg_id = None
			logging.info("User: "+users.email+" unregistered id")
			self.response.out.write('unregistered')
		else:
			logging.info("User: "+users.email+" unregistered ID unsuccessful, Account not found")
			self.response.out.write(self.request.get('email')+' Account not found')
#######################################
application = webapp2.WSGIApplication([
	('/', Login),
	('/register', RegUsersSection),
	('/searchRider', SearchRider),
	('/searchDriver', SearchDriver),
	('/requestRide', RequestRide),
	('/offerRide', OfferRide),
	('/userInfo', UserInfo),
	('/GCMresend', GCMResend),
	('/GCMregister', GCMRegister),
	('/GCMunregister', GCMUnregister),
	('/test', TestRide)
], debug=True)   #remember to change this




