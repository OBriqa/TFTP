from help import *

# Configuració

serverName = 'localhost'
serverPort = 14000

# Opcions

opc = ['timeOut', 'blockSize']
timeOutTemps = 1000
mida = 512
mode = 'octet'

# Variables d'estat

fiError = False
Enviat = False

nAct = 1
nAnt = 0

nAck = -1
nData = 1
timeOut = 0

clientSocket = socket(AF_INET,SOCK_DGRAM)

print("PUT/GET OPERATION UDP | put/get [filename origin] [filename destination] [timeOut]ms [blockSize]B")
operacio = input('> ')
op = operacio.split()

if len(op) == 5:

	if op[0] == 'put' and not fiError:

		# Obrim el fitxer en mode 'octet' o 'netASCII', si falla -> missatge d'error		
		try:
			fd = open(op[1],'rb' if mode == 'octet' else 'r')
			
		except OSError:
			print(f"ERROR | Failed to open file '{op[1]}'")
			fiError = True
			
		if not fiError:

			# Assignem opcions segons l'entrada que indiqui l'usuari

			val = [op[3], op[4]]

			val[0] = int(int(val[0])//1000)
			val[1] = int(log2(int(val[1])))

			val[0] = 1 if val[0] == 0 else val[0]

			clientSocket.sendto(generaRQM(opr['WRQ'], op[2], mode, opc, val), (serverName, serverPort))
			print(f"Enviant solicitud d'escriptura WRQ de l'arxiu {op[1]}...") 

			# Segons la resposta del Servidor, tenim tres opcions
			# --- | OACK 	-> alguna opció acceptada
			# --- | ACK 	-> cap opció acceptada
			# --- | ERROR 	-> petició denegada

			capOpcio = False
			confirmat = False 
			while not confirmat:
				CONFi, addr = clientSocket.recvfrom(mida)
				op = opPACK(CONFi)
				if op == opr['ACK']:
					nAck = decodificaACK(CONFi)
					confirmat = True
					capOpcio = True
				elif op == opr['ERR']:
					op, error = decodificaERROR(CONFi)
					print(error)
					confirmat = True
					fiError = True
				elif op == opr['OACK']:
					nAck = 0
					confirmat = True
					op, opc, val = decodificaOACK(CONFi)

			if capOpcio:
				print("WRQ Acceptat | No s'ha acceptat cap opció, utilitzant valors per defecte")		

			elif confirmat and not fiError:
				timeOutTemps = timeOutTemps if val[0] == 0 else val[0]
				mida = mida if val[1] == 0 else int(pow(2, val[1]))

				print("WRQ Acceptat | S'han acceptat algunes opcions!")	

			elif fiError:
				pass	

			text = fd.read(mida)
			while len(text) > 0 and not fiError:

				while not Enviat:	
					print('--------------------------')

					clientSocket.sendto(generaDATA(nData, text, mode), (serverName, serverPort))
					print(f"enviant DATA nº {nData} ...")

					while (nAck == (nData-1)%65536) and not fiError:
						clientSocket.settimeout(timeOutTemps/1000)
						try:
							CONFi, addr = clientSocket.recvfrom(mida)
							clientSocket.settimeout(None)
							op = opPACK(CONFi)
							
							if op == opr['ACK']:
								nAck = decodificaACK(CONFi)
								print(f"rebent  ACK  nº {nAck} ... ")

							elif op == opr['ERR']:
								op, error = decodificaERROR(CONFi)
								print(error)
								fiError = True

						except: # Tornem a enviar el paquet DATA ja que s'ha excedit el temps d'espera (TO)
							timeOut += 1
							clientSocket.sendto(generaDATA(nData, text, mode), (serverName, serverPort))
							clientSocket.settimeout(None)
							print(f"TO | tornant a enviar DATA nº {nData} ...")

					Enviat = (nAck == nData)
								
				text = fd.read(mida)
				nData = (nData + 1) % 65536
				Enviat = False
			
			# Finalització explícita
			clientSocket.sendto(generaDATA(nData, '' if mode == 'netASCII' else bytes(), mode), (serverName, serverPort))
			fd.close()

			print("timeOut counter: ", timeOut)

	elif op[0] == 'get' and not fiError:
		
		text = bytes()
		nData = 0
		nAnt = 1
		nAck = 1
		
		# Obrim el fitxer en mode 'octet' o 'netASCII', si falla -> missatge d'error		
		try:
			fd = open(op[2],'wb' if mode == 'octet' else 'w')
			
		except OSError:
			print(f"ERROR | Failed to open file '{op[1]}'")
			fiError = True		

		if not fiError:
		
			# Assignem opcions segons l'entrada que indiqui l'usuari

			val = [op[3], op[4]]

			val[0] = int(int(val[0])//1000)
			val[1] = int(log2(int(val[1])))

			val[0] = 1 if val[0] == 0 else val[0]

			clientSocket.sendto(generaRQM(opr['RRQ'], op[1], mode, opc, val), (serverName, serverPort))
			print(f"Enviant solicitud de lectura RRQ de l'arxiu {op[1]}...") 

			# Segons la resposta del Servidor, tenim tres opcions
			# --- | OACK 	-> alguna opció acceptada
			# --- | DATA 	-> cap opció acceptada
			# --- | ERROR 	-> petició denegada

			capOpcio = False
			confirmat = False
			while not confirmat:
				CONFi, addr = clientSocket.recvfrom(mida)
				op = opPACK(CONFi)
				if op == opr['DATA']:
					capOpcio = True
					confirmat = True
					nData, text = decodificaDATA(CONFi)
					print(f"Rebent DATA amb ID {nData}")
				elif op == opr['ERR']:
					op, error = decodificaERROR(CONFi)
					print(error)
					confirmat = True
					fiError = True
				elif op == opr['OACK']:
					nAck = 0
					confirmat = True
					op, opc, val = decodificaOACK(CONFi)
			
			if not fiError:

				if capOpcio:
					print("WRQ Acceptat | No s'ha acceptat cap opció, utilitzant valors per defecte")		

				elif confirmat and not fiError:
					timeOutTemps = timeOutTemps if val[0] == 0 else val[0]
					mida = mida if val[1] == 0 else int(pow(2, val[1]))
					
					print("WRQ Acceptat | S'han acceptat algunes opcions!")	
					
					clientSocket.sendto(generaACK(0), (serverName, serverPort))
					print(f"enviant ACK   nº {nAck} ...")

				elif fiError:
					pass	

				while nData != 1 and not fiError:
					data, addr = clientSocket.recvfrom(mida+4)
					nData, text = decodificaDATA(data)
					print(f"Rebent DATA amb ID {nData} | Confirmació de RRQ")
					
				fd.write(text if mode == 'octet' else text.decode('utf-8'))
			
			while len(text) > 0 and not fiError:

				while not Enviat:	
					print('--------------------------')

					clientSocket.sendto(generaACK(nAck), (serverName, serverPort))
					print(f"enviant ACK   nº {nAck} ...")

					while (nAck == nData):
						clientSocket.settimeout(timeOutTemps/1000) # TO = 1ms
						try:
							data, addr = clientSocket.recvfrom(mida+4)
							clientSocket.settimeout(None)
							nData, text = decodificaDATA(data)
							print(f"rebent  DATA  nº {nData} ...")	
						
						except: # Tornem a enviar el paquet ACK ja que s'ha excedit el temps d'espera (TO)
							timeOut += 1
							clientSocket.sendto(generaACK(nAck), (serverName, serverPort))
							clientSocket.settimeout(None)
							print(f"TO | tornant a enviar ACK nº {nAck} ...")
							
						nAct = nData
					
					if (nAct == (nAnt + 1)%65536):
						fd.write(text if mode == 'octet' else text.decode('utf-8'))
						nAnt = nAct
						
					Enviat = (nAck == (nData-1)%65536)

				nAck = (nAck + 1) % 65536
				Enviat = False
			
			print('--------------------------')
			print("timeOut counter: ", timeOut)
			fd.close()

	else:
		print("ERROR | Incorrect operation")

else:
	print("ERROR | Incorrect operation")
			
clientSocket.close()