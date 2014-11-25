from scapy.all import *
from Queue import Queue
import sys
import threading
import time
import pytds

pkts=Queue()
queries=Queue()
with file("/home/atticus/Desktop/log.txt",'w') as f:
	f.write("")

class Parse(threading.Thread):
	#need to be able to set MTU from cmdline
	def __init__(self,mtu=1500):
		threading.Thread.__init__(self)
		self.die = False
		self.mtu = mtu
		self.frag = {}

	def run(self):
		global pkts
		while not self.die:
			if not pkts.empty():
				self.parse(pkts.get())

	def parse(self,pkt):
		if pkt.payload.payload.sport == 1433:
			#reassesmble pkts if fragged
			key='%s:%s'%(pkt[IP].dst,pkt[TCP].dport)
			if len(str(pkt[IP])) == self.mtu:
				try:
					self.frag[key]+=str(pkt[TCP])[20:]
				except KeyError:
					self.frag[key]=str(pkt[TCP])[20:]
			else:
				try:
					self.parseResp(self.frag[key]+str(pkt[TCP])[20:])
					del self.frag[key]
				except KeyError:
					self.parseResp(str(pkt[TCP])[20:])
		elif pkt.payload.payload.dport == 1433:
			self.parseReq(str(pkt[TCP]).encode('hex')[40:])

	def validAscii(self,h):
		if int(h,16)>31 and int(h,16)<127:
			return True
		return False

	def readable(self,data):
		a=""
		for i in range(0,len(data)/2):
			if self.validAscii(data[i*2:i*2+2]):
				a+=data[i*2:i*2+2].decode("hex")
		return a

	def parseReq(self,data):
		self.println("\n--Req--\n%s\n"%self.readable(data))

	def parseResp(self,data):
		resp=''
		tdssock = pytds._TdsSocket(data)
		try:
			while True:
				tdssock._main_session.find_result_or_done()
		except:
			pass

		for a in tdssock._main_session.results:
			resp+=str(a)+"\n"

		try:
			resp=tdssock._main_session.messages[0]['message']
		except:
			pass

		if len(resp) == 0:
			resp = 'error parsing response'
		self.println("--Resp--\n%s"%resp)

	def println(self,s):
		with file("/home/atticus/Desktop/log.txt",'a') as f:
			f.write(s)
		print(s)

class Scout(threading.Thread):
	def __init__(self):
			threading.Thread.__init__(self)
			self.die = False
		
	def run(self):
		self.scout()

	def scout(self):
		while not self.die:
			try:
				sniff(prn=self.pushToQueue,filter="tcp and host 192.168.37.135",store=0,timeout=5)
			except:
				self.die = True

	def pushToQueue(self,pkt):
		global pkts
		pkts.put(pkt)
	
class Pillage(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.die = False

	def run(self):
		global queries
		while not self.die:
			if not queries.empty():
				q = queries.get()
				print('[*] Executing query:\t%s'%q.split('||')[0])
				print('[*] Targetting:\t%s'%q.split('||')[1])

def writeResults():
	print('[*] Enter filepath to write to:')
	path = raw_input("> ")
	#with open(path,'w') as f:
	print('[*] Writing results to:\t%s'%path)	 

def printResults():
	print('[*] Results so far:')

def pillage():
	global queries
	print('[*] Enter query to execute:')
	query = raw_input("> ")
	print('[*] Enter IP:port to execute against:')
	dst = raw_input("> ")
	queries.put(query+"||"+dst)

def parseInput(input):
	if input == 'w':
		writeResults()
	elif input == 'p':
		printResults()
	elif input == 'r':
		pillage()
	elif input == 'q':
		raise KeyboardInterrupt
	else:
		print('Unknown command entered')	

def main():
	print('==Welcome to SQLViking!==')

	t1 = Scout()
	t2 = Parse()
	t3 = Pillage()
	t1.start()
	t2.start()
	t3.start()
	
	while True:
		print('\n\n[*] Menu Items:')
		print('\tw - dump current results to file specified')
		print('\tp - print current results to screen')
		print('\tr - run a query against a specified DB')
		print('\tq - quit')
		try:
			parseInput(raw_input("> "))
		except KeyboardInterrupt:
			print('\n[!] Shutting down...')
			t1.die = True
			t2.die = True
			t3.die = True
			break
		time.sleep(1)
	
if __name__ == "__main__":
	main()
