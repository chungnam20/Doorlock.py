import RPi.GPIO as GPIO
import time
import threading
import socket
import sys
import os
import picamera
#import glob

# 네이버 서버
#host = '118.67.129.197'
#port = 7000

#host = '127.0.0.1'
host = '192.168.0.6'
port = 8000
clnt_sock = 0

recv_data = ''
send_data = ''
ncnt = 0
th_send_stop = 0
th_stop = 0
recv_check = 0

th_recv = ()
th_send = ()

# 데이터 수신
def th_recv_data():
	global clnt_sock, recv_data, th_send_stop, ncnt, th_stop
	clnt_sock.settimeout(1)
	while True:
		try:
			if th_stop:
				return
			data = clnt_sock.recv(1024)
			data = data.decode()
			if data == '\n':
				pass
			elif data == '$OK$':
				recv_check=1
				print('수신확인')
			elif data:
				print(data)
				recv_data = data
			else:
				ncnt = ncnt+1
				if ncnt>5:
					print('서버와의 연결이 끊어졌습니다')
					clnt_sock.close()
					th_send_stop = 1
					time.sleep(1)
					con()
					return

		except socket.timeout:
			continue
		except ConnectionResetError:
			print('[ConnectionResetError]')
			print('서버와의 연결이 끊어졌습니다')
			clnt_sock.close()
			th_send_stop = 1
			time.sleep(1)
			con()
			return

# 데이터 전송
def th_send_data():
	global clnt_sock, send_data, th_send_stop, th_stop
	while True:
		if send_data:
			clnt_sock.sendall(send_data.encode())
			send_data=''
		if th_send_stop or th_stop:
			th_send_stop = 0
			break
		time.sleep(0.1)

# 서버연결
def con():
	global clnt_sock, th_recv, th_send, th_stop, clnt_sock
	print('서버에 연결중..')
	while True:
		try:
			if th_stop:
				return
			time.sleep(1)
			clnt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			clnt_sock.settimeout(1)
			clnt_sock.connect((host,port))
			print('connected')
			print(clnt_sock) #
			clnt_sock.sendall('Test Message'.encode())
			th_recv = threading.Thread(target=th_recv_data)
			th_recv.start()
			th_send = threading.Thread(target=th_send_data)
			th_send.start()
			break
		except socket.timeout:
			time.sleep(0.5)
			continue
		except ConnectionRefusedError:
			time.sleep(0.5)
			continue


# 사진 촬영
camera = picamera.PiCamera()
camera.resolution = (1920,1440)
camera.framerate = 30
photo_pending = False
def photo():
	global photo_pending, clnt_sock
	photo_pending = True
	print('촬영중..')
	tim = time.localtime()
	path = '/home/pi/Project/image/'
	name = str(tim.tm_year)+'-'+str(tim.tm_mon)+'-'+str(tim.tm_mday)+'_'+\
		str(tim.tm_hour)+':'+str(tim.tm_min)+':'+str(tim.tm_sec)+'.jpg'
	img = path + name

	camera.capture(img)
	print(img,'저장됨')
	try:
		print('사진 전송중..')
		size = os.path.getsize(img)
		mess = 'IMG$'+name+'$'+str(size)
		clnt_sock.sendall(mess.encode()) # 파일이름,크기 송신
		rf = open(img, 'rb')
		time.sleep(0.1)
		img_data = rf.read(8192)
		while img_data:
			clnt_sock.sendall(img_data)
			time.sleep(0.01)
			img_data = rf.read(8192)
#		print('전송')
	finally:
		rf.close()
	photo_pending = False


# 도어락
buzz = 27
servoPin = 4
melody = [262,294,330,349,392,440,494,524,1,1]

rowPin = [21,20,16,26]
colPin = [19,13,6,5]

list = ['123A','456I','789J','*0#K']

chBuf = ''
pswd = '1234'	# 초기 비밀번호
pswd_in = ''
pswd_new = ''
pswd_new2 = ''
cnt = 0

GPIO.setmode(GPIO.BCM)
GPIO.setup(rowPin, GPIO.OUT, initial=0)
GPIO.setup(buzz, GPIO.OUT, initial=0)
GPIO.setup(servoPin, GPIO.OUT, initial=0)
GPIO.setup(colPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# 키패드
def th_keypad():
	global chBuf, th_stop
	while True:
		if th_stop:
			break
		for i in range(4):
			GPIO.output(rowPin[i], 1)
			for j in range(4):
				if GPIO.input(colPin[j]):
					time.sleep(0.05)
					if GPIO.input(colPin[j]):
						chBuf = list[i][j]
						# print(chBuf)
						dcnt = 0
						while True:
							time.sleep(0.01)
							if not GPIO.input(colPin[j]):
								dcnt=dcnt+1
							if dcnt>5:
								break
			GPIO.output(rowPin[i], 0)

th = threading.Thread(target = th_keypad)
th.start()


buz = GPIO.PWM(buzz, 400)		# 부저
servo = GPIO.PWM(servoPin, 50)	# 서보모터
servo.start(2)			  	# 닫힌상태

mode = 'n'  	# 초기모드


def sound_open():
	buz.start(50)
	for i in range(3):
		buz.ChangeFrequency(melody[i*2]*2)
		time.sleep(0.3)
	buz.stop()

def sound_close():
	buz.ChangeFrequency(melody[2]*2)
	buz.start(50)
	time.sleep(0.2)
	buz.ChangeFrequency(melody[0]*2)
	time.sleep(0.2)

def sound_false():
	for i in range(4):
		buz.start(50)
		buz.ChangeFrequency(300)
		time.sleep(0.08)
		buz.stop()
		time.sleep(0.08)

def sound_change():
	buz.ChangeFrequency(500)
	buz.start(50)
	time.sleep(0.4)
	buz.stop()


def chmod():
	global mode, pswd, pswd_in, pswd_new, pswd_new2
	if mode == 'n':
		print('비밀번호 변경모드 - 이전 비밀번호 입력')
		pswd_in = ''
		pswd_new = ''
		pswd_new2 = ''
		sound_change()
		mode = 'bef'

	elif mode == 'bef':
		if pswd_in == pswd:
			print('새 비밀번호 입력')
			sound_change()
			mode = 'ch'
		else:
			print('비밀번호를 틀렸습니다')
			sound_false()
			mode = 'n'

	elif mode == 'ch':
		print('한번더 입력')
		sound_change()
		mode = 'ch2'

	elif mode == 'ch2':
		if pswd_new == pswd_new2:
			print('비밀번호 변경완료')
			for i in range(3):
				buz.ChangeFrequency(500)
				buz.start(50)
				time.sleep(0.2)
				buz.stop()
				time.sleep(0.1)
			pswd = pswd_new
			mode = 'n'
		else:
			print('일치하지 않습니다')
			sound_false()
			mode = 'n'

def inmod():
	global mode, pswd, pswd_in, cnt, send_data
	if mode == 'n':
		mode = 'in'
		pswd_in = ''
		print('비밀번호 입력모드')
		for i in range(2):
			buz.ChangeFrequency(500)
			buz.start(50)
			time.sleep(0.08)
			buz.stop()
			time.sleep(0.08)

	elif mode == 'in':
		if pswd_in == pswd:
			print('문이 열렸습니다')
			servo.ChangeDutyCycle(6.9)
			buz.start(50)
			sound_open()
			cnt = 0
		else:
			cnt = cnt+1
			print('비밀번호를 ' + str(cnt) + '회 틀렸습니다')
			if cnt > 2:
				send_data = '비밀번호 입력시도 ' + str(cnt) + '회'
				if not photo_pending:
					threading.Thread(target=photo).start()
			send_data
			servo.ChangeDutyCycle(2.0)
			sound_false()
		pswd_in = ''
		mode = 'n'


try:
	th = threading.Thread(target = con)
	th.start()

	while True:
		if chBuf:
			if chBuf == '*':		# 입력모드
				inmod()

			elif chBuf == 'A':		# 비밀번호 변경모드
				chmod()

			elif chBuf == 'I':		# 촬영
				if not photo_pending:
					threading.Thread(target=photo).start()

			elif chBuf == 'K':
				break

			elif chBuf == '#' and mode == 'n':
				print('문이 잠깁니다')
				servo.ChangeDutyCycle(2.0)
				sound_close()

			else:
				if mode != 'n' and chBuf >= '0' and chBuf <= '9':
					if mode == 'ch':
						pswd_new = pswd_new + chBuf
						print('*'*len(pswd_new))
					elif mode == 'ch2':
						pswd_new2 = pswd_new2 + chBuf
						print('*'*len(pswd_new2))
					else:
						pswd_in = pswd_in + chBuf
						print('*'*len(pswd_in))
					buz.ChangeFrequency(500)
					buz.start(50)

		if recv_data == 'open':
			recv_data=''
			print('문이 열렸습니다')
			servo.ChangeDutyCycle(6.9)
			sound_open()
			send_data = '문이 열렸습니다'

		elif recv_data == 'close':
			recv_data=''
			print('문이 잠깁니다')
			servo.ChangeDutyCycle(2.0)
			sound_close()
			send_data = '문이 잠겼습니다'

		chBuf = ''
		time.sleep(0.09)
		buz.stop()


except KeyboardInterrupt:
	th_stop = 1					# 종료플래그
finally:
	th_stop = 1
	time.sleep(2)
	clnt_sock.close()
	GPIO.cleanup()
	print('종료')
