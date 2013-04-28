import os
import cgi
import datetime
import urllib
import wsgiref.handlers
import json
import logging

from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

class ScoreIncrement(db.Model):
  score = db.IntegerProperty()

class User(db.Model):
  """Models a individual User entry with some properties."""
  user_id = db.StringProperty()
  score = db.IntegerProperty()
  level = db.IntegerProperty()

def user_key(user_id=None):
  """Constructs a Datastore key for a User entity with user_id."""
  return db.Key.from_path('User', user_id or 'default_user_id')


class MainPage(webapp.RequestHandler):
    def get(self):
        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        template_values = {
            'url': url,
            'url_linktext': url_linktext,
        }

        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, template_values))

def get_level(score):
  if score < 10:
    return 1
  elif score < 50:
    return 2
  elif score < 200:
    return 3
  elif score < 1000:
    return 4
  elif score < 2000:
    return 5
  else:
    return 6

class UserAPI(webapp.RequestHandler):

  current_user = users.get_current_user()
  user_id = current_user.user_id() if current_user else None
  nickname = current_user.nickname() if current_user else 'Anonymous'
  score = 0
  level = 0

  def getUser(self):
    return User(parent=db.Key.from_path('User', 'all_users'), key_name=self.user_id)

  def updateUser(self):
    user = self.getUser()
    user.user_id = self.user_id
    user.score = self.score
    user.level = self.level
    user.put()

  def post(self):
    score = self.request.get('score')
    if score:
      logging.debug("Trying to store score")
      score_increment = ScoreIncrement(parent=user_key(self.user_id))
      score_increment.score = int(score)
      score_increment.put()

      scores_query = ScoreIncrement.all().ancestor(user_key(self.user_id))
      scores = scores_query.fetch(100)

      for s in scores:
        self.score += s.score

      self.level = get_level(self.score)

      self.updateUser()
    else:
      logging.debug("No score provided")
    
    self.redirect('/user')

  def get(self):
    user = db.get(db.Key.from_path('User', 'all_users', 'User', self.user_id)) 
    self.level = user.level
    self.score = user.score

    self.response.headers['Content-Type'] = 'application/json'   
    obj = {
    'user_id': self.user_id,
    'nickname': self.nickname,
    'level': self.level, 
    'score': self.score
    } 
    self.response.out.write(json.dumps(obj))


application = webapp.WSGIApplication([
  ('/', MainPage),
  ('/user', UserAPI)
], debug=True)


def main():
  logging.getLogger().setLevel(logging.DEBUG)
  run_wsgi_app(application)


if __name__ == '__main__':
  main()

