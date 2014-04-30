#!/usr/bin/env python

import os
import urllib
import jinja2
import webapp2
import uuid
import json

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.api import channel

JINJA_ENVIRONMENT = jinja2.Environment(
	loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
	extensions=['jinja2.ext.autoescape'],
	autoescape=True)

def chatroom_key(chatroom_name):
	return ndb.Key('Chatroom', chatroom_name)

def send_message_to_chatroom_connections(content, chatroom):
	ndb.get_context().set_memcache_policy(False)
	ndb.get_context().set_cache_policy(False)
	
	connections_query = Connection.query(ancestor=chatroom_key(chatroom))
	connections = connections_query.fetch(40)

	author = users.get_current_user().nickname()
	message = json.dumps({'content': content,'author': author})

	for c in connections:
		channel.send_message(c.channel_id, message)

class ChatLine(ndb.Model):
	author = ndb.UserProperty()
	content = ndb.StringProperty(indexed=False)
	date = ndb.DateTimeProperty(auto_now_add=True)

class Connection(ndb.Model):
	channel_id = ndb.StringProperty()
	date = ndb.DateTimeProperty(auto_now_add=True)

class ChatPage(webapp2.RequestHandler):
	def get(self, chatroom="main"):

		channel_id = uuid.uuid4().hex
		token = channel.create_channel(channel_id)
		ckey = chatroom_key(chatroom)

		# Store the connection
		connection = Connection(parent=ckey)
		connection.channel_id = channel_id
		connection.put()

		template_values = {
			'chatroom': urllib.quote_plus(chatroom),
			'token': token
		}

		template = JINJA_ENVIRONMENT.get_template('index.html')
		self.response.write(template.render(template_values))

class ChatPost(webapp2.RequestHandler):
	def post(self):
		chatroom = self.request.get('chatroom')
		content = self.request.get('content')

		send_message_to_chatroom_connections(content, chatroom)

class ConnectionDisconnect(webapp2.RequestHandler):
	def post(self):
		channel_id = self.request.get('from')
		key_query = ndb.gql("SELECT __key__ FROM Connection WHERE channel_id = :1", channel_id)
		key_to_delete = key_query.get()
		key_to_delete.delete()

app = webapp2.WSGIApplication([
	('/', ChatPage),
	('/chatpost', ChatPost),
	('/(\w+)', ChatPage),
	('/_ah/channel/disconnected/', ConnectionDisconnect)
], debug=True)