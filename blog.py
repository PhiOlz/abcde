import os
import webapp2
import jinja2
import hashlib
import hmac
import random
import re
import string
from jinja2 import filters, environment
from google.appengine.ext import db
from dbmodel import Users
from dbmodel import Comments
from dbmodel import Likes
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)
def getcomments(post_id):
    coms = db.GqlQuery("select * from Comments where post_id=" + post_id + " order by created desc")
    return coms;
jinja_env.filters['getcomments'] = getcomments
def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)
class Post(db.Model):
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)
    def render(self, user):
        self._render_text = self.content.replace('\n', '<br>')
        t = jinja_env.get_template("post.html")
        return t.render(p = self)        
class BlogHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
    def render_str(self, template, **params):
        return render_str(template, **params)
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))
def render_post(response, post):
        response.out.write('<b>' + post.subject + '</b><br>')
        response.out.write(post.content)
class MainPage(BlogHandler):
  def get(self):
      self.redirect('/blog')
def blog_key(name = 'default'):
    return db.Key.from_path('blogs', name)     
class BlogFront(webapp2.RequestHandler):
    def get(self):
            posts = db.GqlQuery("select * from Post order by created desc limit 10")
            t = jinja_env.get_template('front.html')
            self.response.out.write(t.render(posts=posts))
class PostPage(webapp2.RequestHandler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)
        if not post:
            self.error(404)
            return
            t = jinja_env.get_template('permalink.html')
            self.response.out.write(t.render(p=post))
class NewPost(webapp2.RequestHandler):
    def get(self, post_id):
        post=None
        if int(post_id) > 0 :
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)
            t = jinja_env.get_template('newpost.html')
            self.response.out.write(t.render(p=post))
    def post(self, p_id):
            subject = self.request.get('subject')
            content = self.request.get('content')
            post = None
            if int(p_id) > 0:
                key = db.Key.from_path('Post', int(p_id), parent=blog_key())
                if key:
                    post = db.get(key)                        
            if subject and content:
                if post:
                    post.subject = subject
                    post.content = content
                    post.put()
                else:
                    post = Post(parent = blog_key(), subject = subject, 
                         content = content)
                    post.put()
                self.redirect('/blog')
            else:
                error = "subject and content, please!"
                t = jinja_env.get_template('newpost.html')
                self.response.out.write(t.render(p=post, u=user))
def deletePost(post_id):
    if int(post_id) > 0 :
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)
        if post:
            coms = db.GqlQuery(
             "SELECT * FROM Comments WHERE post_id=" + str(post.key().id()))
            for c in coms:
                c.delete()
            likes = db.GqlQuery(
             "SELECT * FROM Likes WHERE post_id=" + str(post.key().id()))
            for l in likes:
                l.delete()
            post.delete()
class DelPost(webapp2.RequestHandler):
    def get(self, post_id):
        if int(post_id) > 0 :
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)
            deletePost(post.key().id())
            self.redirect('/blog')
class DelComment(webapp2.RequestHandler):
    def get(self, comment_id):
        comment=None
        post_id = None
        if int(comment_id) > 0 :        
            key = db.Key.from_path('Comments', int(comment_id), parent=blog_key())
            comment = db.get(key)
            pkey = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(pkey)
            post.count_comment -= 1
            post.put()               
        if post_id :
            self.redirect('/blog/')
class CommentPost(webapp2.RequestHandler):
    def get(self, post_id):
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)                        
            if post:
                coms = getcomments(post_id)
                t = jinja_env.get_template('comment.html')
                self.response.out.write(t.render(post=post, coms=coms))
    def post(self, post_id):
            comment = self.request.get('comment')
            u=123456789
            com = Comments(parent = blog_key(), post_id = int(post_id), user_id=u, comment = comment)
            com.put()
            self.redirect('/blog/')
class EditComment(webapp2.RequestHandler):
    def get(self, comment_id):
        if int(comment_id) > 0:
            ckey = db.Key.from_path('Comments', int(comment_id), parent=blog_key())
            com = db.get(ckey)        
            if com:
                pkey = db.Key.from_path('Post', int(com.post_id), parent=blog_key())
                post = db.get(pkey)
                t = jinja_env.get_template('comment-edit.html')
                self.response.out.write(t.render(post=post, com=com))       
    def post(self, com_id):
            updated_comment = self.request.get('comment')
            com.comment = updated_comment
            com.put()
            self.redirect('/blog/comment/%s' % str(com.post_id))
class Search(webapp2.RequestHandler):
    #def render(self, user):
        #self._render_text = self.content.replace('\n', '<br>')
        #t = jinja_env.get_template("post2.html")
        #return t.render(p2 = self)
    def get(self):
        posts = db.GqlQuery("select * from Post")
        t2 = jinja_env.get_template('front2.html')
        self.response.out.write(t2.render(posts=posts))
        
class FlushDb(BlogHandler):
    def get(self):
        posts = Post.all()
        for p in posts:
            p.delete()
        comments = Comments.all()
        for c in comments:
            c.delete()
class DumpDb(BlogHandler):
    def get(self):
        posts = Post.all()
        self.response.out.write("<table>")
        self.response.out.write("<tr><th>Blog Posts</th></tr>")        
        save_id=0
        self.response.out.write("<tr><th>PostID</th><th>Subject</th></tr>")
        for p in posts:
            self.response.out.write("<tr><td>" + str(p.key().id()) + "</td>")
            self.response.out.write("<td>p.subject</td></tr>")
            save_id = p.key().id()
        post = Post.get_by_id(save_id)
        if post == None:
            self.response.out.write("<tr><td>Post.get_by_id(" + str(save_id) + ")=" + str(post) +"</td></tr>")        
        else :
            self.response.out.write("<tr><td>Post.get_by_id()=" + str(post.key().id()) +"</td></tr>")
        self.response.out.write("<tr><th>PostID</th><th>CommentID</th></tr>")
        comments = Comments.all()
        comment_id = 0
        for c in comments:
            self.response.out.write("<tr><td>" + str(c.post_id) +"</td>")
            self.response.out.write("<td>" + str(c.key().id()) + "</td></tr>")
            comment_id = c.key().id()
        if comment_id > 0:
            c = Comments.get_by_id(comment_id)
            if c:
                self.response.out.write("<tr><td> Comments.get_by_id("+ str(comment_id) + ")")
                selt.response.out.write("=" + c.key().id() + "</td></tr>")
            else : 
                self.response.out.write("<tr><td>Comments.get_by_id(id) return None</td></tr>")
            coms = db.GqlQuery(
                "SELECT * FROM Comments WHERE id=" + str(comment_id))
            c = coms.fetch(1)
            if c:
                self.response.out.write("<tr><td>Select on Comments return a record.</td></tr>")
        else:
            self.response.out.write("<tr><td>Zero Comments in db</td></tr>")
        key = db.Key.from_path('Post', 101, parent=blog_key())
        post = db.get(key)
        if post:
            self.response.out.write("<tr><td>id=101 returns post</td></tr>")
        else :
            self.response.out.write("<tr><td>id=101 return None</td></tr>")    
            
app = webapp2.WSGIApplication([
       ('/', MainPage),
       ('/blog/?', BlogFront),
       ('/blog/([0-9]+)', PostPage),
       ('/blog/newpost/([0-9]+)', NewPost),
       ('/blog/delpost/([0-9]+)', DelPost),
       ('/blog/delcom/([0-9]+)', DelComment),
       ('/blog/editcom/([0-9]+)', EditComment),
       ('/blog/comment/([0-9]+)', CommentPost),
       ('/blog/flushdb', FlushDb),
       ('/blog/dumpdb', DumpDb),
       ('/blog/post2', Search),
       ],
      debug=True)
