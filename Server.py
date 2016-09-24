
# gaooz.com
# 2016/6

import tornado.ioloop
import tornado.web
import tornado.escape
import tornado.websocket
import tornado.httpclient
import tornado.httpserver
import socket
import os
import time
import multiprocessing
import types

class Main(tornado.web.RequestHandler):
    def get(self):
        self.render("./app/index.html")

class EchoWebSocket(tornado.websocket.WebSocketHandler):
    client_list = [-1,-1,-1,-1,-1]
    client_start_flag = [False,False,False,False,False]
    process_exec_command = "this is a temporary value,the variable should be a process"

    def open(self):
        try:
            self.id = self.client_list.index(-1)
        except ValueError,e:
            print "The number of clients has been reached to the maximum..."
            self.write_message("The number of clients has been to the maximum,please exit!")
            self.id = -1
            return None
        self.client_list[self.id] = 0
        self.write_message("Connect Success...<br/>"+"Now you can start to monitor the Web log...")
        print("WebSocket opened,id:"+str(self.id))

    def on_message(self, message):
        if self.id==-1:
            self.write_message("The max num of clients is 5,now please exit...")
            return None

        print (u"Message form client-"+str(self.id)+": " + message)
        # convert the json string to the dict object
        message = eval(message) # or json.loads(message)
        if message["command"]=="start":
            EchoWebSocket.client_start_flag[self.id] = True
            if type(EchoWebSocket.process_exec_command) is types.StringType or not EchoWebSocket.process_exec_command.is_alive():
                print "process is not start,Now starting..."
                # ---- You can set the command in ./config/command_config----
                #command = "mpstat -P ALL 1"
                with open(r"./config/command_config","r") as command_file:
                    command = command_file.readline()
                    command = command.replace("\n","")
                EchoWebSocket.process_exec_command = multiprocessing.Process(target=self.execute_command,args=(command+" > ./res.info",))
                EchoWebSocket.process_exec_command.start()

            if self.isset():
                self.killAllChildProcess()
            self.write_message("Start...")

            # get the filter word from client
            self.filter_word1 = message["filter1"]
            self.filter_word2 = message["filter2"]
            self.filter_flag = message["flag"]

            # The second child process takes responsible for reading data from the result file which the command generated!
            self.child2 = multiprocessing.Process(target=self.read_data)
            self.child2.start()
        else:
            print message
            EchoWebSocket.client_start_flag[self.id] = False
            self.killAllChildProcess()
            if self.client_list.count(-1) == 4 or True not in EchoWebSocket.client_start_flag:
                self.killProcess_exec_command()
            self.write_message("Stop...")
            
    def on_close(self):
        if self.id==-1:
            return None
        self.client_list[self.id] = -1
        EchoWebSocket.client_start_flag[self.id] = False
        # kill all process run on the client
        # ...
        self.killAllChildProcess()
        if self.client_list.count(-1) == 5 or True not in EchoWebSocket.client_start_flag:
            self.killProcess_exec_command()
        print("WebSocket closed,id:"+str(self.id))

    def execute_command(self,command):
        print command
        os.popen(command)

    def read_data(self):
        time.sleep(1)
        print "read_data..."
        with open(r"./res.info") as f:
            f.seek(0,2)
            while True:
                pos = f.tell()
                line = f.readline()
                if not line:
                    f.seek(pos)
                else:
                    line = line.replace("\n","<br/>")
                    #line = line.replace(" ","&nbps;")
                    # filter line under the given conditions
                    if self.filter_word1=="" and self.filter_word2=="":
                        self.write_message(line)
                    else:
                        if self.filter_word1!="" and self.filter_word2!="":
                            if self.filter_flag == "true":
                                # and
                                if line.find(self.filter_word1)!=-1 and line.find(self.filter_word2)!=-1:
                                    self.write_message(line)
                            else:
                                # or
                                if line.find(self.filter_word1)!=-1 or line.find(self.filter_word2)!=-1:
                                    self.write_message(line)
                        elif self.filter_word1!="" and self.filter_word2=="":
                            if line.find(self.filter_word1)!=-1:
                                self.write_message(line)
                        else:
                            if line.find(self.filter_word2)!=-1:
                                self.write_message(line)

    def killAllChildProcess(self):
        if self.isset():
            if self.child2.is_alive():
                os.popen("kill -9 "+str(self.child2.pid))
                self.child2.join()
            else:
                print "child2 is not alive"
        else:
            print "children process is not set"

    def killProcess_exec_command(self):
        if type(EchoWebSocket.process_exec_command) is types.StringType:
            return None
        if EchoWebSocket.process_exec_command.is_alive():
            os.popen("kill -9 "+str(EchoWebSocket.process_exec_command.pid))
            EchoWebSocket.process_exec_command.join()
        # del the res file
        if os.path.exists("./res.info"):
            os.remove("./res.info")

    def isset(self):
        '''
            charge the variable self.child2 whether set or not
        '''
        try:
            print self.child2
        except AttributeError,e:
            return False
        return True


application = tornado.web.Application([
    (r"/", Main),

    (r"/websocket-server",EchoWebSocket),
    
    (r"/static/(.*)",tornado.web.StaticFileHandler,{"path":os.path.join(os.path.dirname(__file__),"static")}),

],debug=False)


# You should know that Tornado is a single process and single thread model,
# WebSocket is not single instance,not like java servlet...

if __name__=="__main__":
    server = tornado.httpserver.HTTPServer(application)
    server.bind(9009)
    server.start(1) # only one process
    tornado.ioloop.IOLoop.instance().start()
