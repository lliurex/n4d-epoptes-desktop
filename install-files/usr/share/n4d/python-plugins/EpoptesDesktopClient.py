import subprocess
import os
import threading
import time
import socket
import shutil
import n4d.responses

from hashlib import md5
from mmap import mmap, ACCESS_READ

class EpoptesDesktopClient:
	
	def __init__(self):
		
		self.epoptes_certificate="/etc/epoptes/server.crt"
		self.current_md5=None
		self.cert_ready_timestamp=None
		self.server_name="server"
			
		self.default_timeout=15
		self.server_retest_timeout=60*3
		
		if not os.path.exists("/etc/epoptes"):
			os.makedirs("/etc/epoptes/")
		
	#def init
	
	def startup(self,options):
		
		# if there is a certificate and it is valid
		# we should try to avoid restarting epoptes-client service
		# main loop will check if server's cert is the same as 
		# client current one
		if os.path.exists(self.epoptes_certificate):
			self.current_md5=self.get_certificate_md5()
			self.cert_ready_timestamp=int(time.time())
		
		self.main_loop()
		
	#def startup
	

	def get_certificate_timestamp(self):
		
		return n4d.responses.build_successful_call_response(self.cert_ready_timestamp)
		
	#def get_certificate_timestamp
	
	
	def main_loop(self):
		
		t=threading.Thread(target=self._main_loop)
		t.daemon=True
		t.start()
		
	#def main_loop
	
	def _main_loop(self):
		
		while True:
			
			timeout=self.default_timeout
			
			if self.is_server_available():
				if self.current_md5==None:
					if self.configure_epoptes():
						timeout=self.server_retest_timeout
				else:
					if self.check_remote_certificate():
						timeout=self.server_retest_timeout
					else:
						if self.configure_epoptes():
							timeout=self.server_retest_timeout

			time.sleep(timeout)	
		
	#def main_loop
	
	def is_server_available(self):
		
		try:
			socket.gethostbyname(self.server_name)
			return True
		except:
			return False
		
	#def is_server_available
	
	def configure_epoptes(self):
		
		if self.get_epoptes_certificate():
			self.restart_epoptes_client()
			self.current_md5=self.get_certificate_md5()
			self.cert_ready_timestamp=int(time.time())
			
			return True
			
		return False
		
	#def configure_epoptes_certificate
	
	def check_remote_certificate(self):
		
		# stolen from epoptes-client
		ret=os.system("openssl s_client -connect %s:789 </dev/null 2>/dev/null | sed '/-----BEGIN CERTIFICATE-----/,/-----END CERTIFICATE-----/!d' > %s.tmp"%(self.server_name,self.epoptes_certificate))
		if ret==0:
			cert=self.get_certificate_md5("%s.tmp"%self.epoptes_certificate)
			if os.path.exists("%s.tmp"%self.epoptes_certificate):
				os.remove("%s.tmp"%self.epoptes_certificate)
			if cert == self.current_md5:
				return True			
				
		return False
		
	#def check_remote_certificate
	
	def get_epoptes_certificate(self):
		
		execute=False
		p=subprocess.Popen(["ps aux | grep 'epoptes-client -c' | wc -l"],shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		output=p.communicate()[0]

		if type(output) is bytes:
			output=output.decode()

		try:
			t=int(output.strip("\n"))
			if t<=2:
				execute=True
		except:
			execute=False
			
		if execute:
			ret=os.system("epoptes-client -c")
			if ret==0:
				return True
			
		return False
		
	#def get_epoptes_certificate
	
	def get_certificate_md5(self,cert_path=None):
		
		if cert_path == None:
			cert_path = self.epoptes_certificate
		
		try:
			with open(cert_path) as file, mmap(file.fileno(), 0, access=ACCESS_READ) as file:
				return md5(file).hexdigest()
		except Exception as e:
			return None
			
	#def get_certificate_md5
	
	def restart_epoptes_client(self):
		
		os.system("systemctl restart epoptes-client")
		
	#def restart_epoptes_client
	
	
if __name__=="__main__":
		edc=EpoptesDesktopClient()
		print(edc.get_certificate_md5())