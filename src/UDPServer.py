from help import *

# Opcions

timeOutTemps = 1
mida = 512

# Variables d'estat

fiError = False
nAct = 0
nAnt = 0

# Configuració

serverPort = 14000
serverSocket = socket(AF_INET,SOCK_DGRAM)
serverSocket.bind(('',serverPort))


print ('Servidor ACTIU...')

while not fiError:
	
	# Reiniciem les variables d'estat per a cada petició

	nAck = 0
	nData = 0
	nAct = 0
	nAnt = 0
	
	# Rebem primer l'operació que ha demanat el Client
	RQ, addr = serverSocket.recvfrom(mida)
	op, nomFitxer, mode, opc, val = decodificaRQM(RQ)
	
	print(f"\nCLIENT ({addr[0]}) CONNECTAT")
	print("---------------------------------")

	if op == opr['WRQ']:

		# Si el fitxer sobre el que volem escriure ja existeix, enviem un paquet d'error
		if os.path.isfile(nomFitxer):
			serverSocket.sendto(generaERROR(6, err[6]), addr)
			fiError = True
			
		else:

			# Obrim el fitxer en mode 'octet' o 'netASCII', si falla -> missatge d'error		
			try:
				fd = open(nomFitxer,'wb' if mode == 'octet' else 'w')
				
			except OSError:
				error = f"No s'ha pogut obrir l'arxiu {nomFitxer}"
				serverSocket.sendto(generaERROR(0, error), addr)
				fiError = True
		
		if not fiError:

			# Acceptem / rebutjem les opcions proposades segons els criteris del Servidor (arbitraris)
			# Utilitzem els valors per defecte del Servidor en cas de rebutjar alguna opció

			acceptat_a = (opc[0] == 'timeOut'   and (val[0] >= 1 and val[0] <= 255))
			acceptat_b = (opc[1] == 'blockSize' and (val[1] >= 5 and val[1] <= 11))

			acceptat = acceptat_a or acceptat_a

			val[0] = (timeOutTemps if not acceptat_a else val[0])
			val[1] = (int(log2(mida)) if not acceptat_b else val[1])  

			# Segons les opcions que accepti el Servidor, tenim tres opcions
			# --- | OACK 	-> alguna opció acceptada
			# --- | ACK 	-> cap opció acceptada
			# --- | ERROR 	-> petició denegada

			if acceptat:
				mida = mida if not acceptat_b else int(pow(2, val[1]))
				serverSocket.sendto(generaOACK(opc, val), addr)
				pass

			elif not acceptat and not fiError:
				serverSocket.sendto(generaACK(nAck), addr)
				pass

			elif fiError:
				pass


		if not fiError:
			
			data, addr = serverSocket.recvfrom(mida+4)
			nData, text = decodificaDATA(data) 
			print(f"rebent DATA amb ID {nData} i escrivint a {nomFitxer} ...") 
			
			nAct = nData

			nAck = (nAck + 1) % 65536
			serverSocket.sendto(generaACK(nAck), addr)
			
			while len(text) > 0 and not fiError:
				
				if (nAct == (nAnt + 1)%65536):
					try:
						fd.write(text if mode == 'octet' else text.decode('utf-8'))
						nAnt = nAct
					except OSError as e:	# Si ens quedem sense espai, enviem un paquet d'ERROR (3)
						if e.errno == errno.ENOSPC:
							serverSocket.sendto(generaERROR(3, err[3]), addr)
				
				data, addr = serverSocket.recvfrom(mida+4)
				nData, text = decodificaDATA(data) 
				
				nAck = nData % 65536
				serverSocket.sendto(generaACK(nAck), addr)
				
				nAct = nData
				print(f"rebent DATA nº {nData} i enviant ACK nº {nAck} ... ") 
					
			print(f"Arxiu {nomFitxer} REBUT correctament")
			print("---------------------------------")
			
			fd.close()

	elif op == opr['RRQ']:

		# Reiniciem les variables d'estat per a cada petició

		text = bytes()
		nData = 1
		nAck = -1
		nAnt = -1

		try:
			# Obrim el fitxer en mode 'octet' o 'netASCII', si falla -> missatge d'error		
			fd = open(nomFitxer,'rb' if mode == 'octet' else 'r')
			
		except FileNotFoundError:
			serverSocket.sendto(generaERROR(1, err[1]), addr)
			fiError = True
				
		if not fiError:

			# Acceptem / rebutjem les opcions proposades segons els criteris del Servidor (arbitraris)
			# Utilitzem els valors per defecte del Servidor en cas de rebutjar alguna opció

			acceptat_a = (opc[0] == 'timeOut'   and (val[0] >= 1 and val[0] <= 255))
			acceptat_b = (opc[1] == 'blockSize' and (val[1] >= 5 and val[1] <= 11))

			acceptat = acceptat_a or acceptat_a

			val[0] = (0 if not acceptat_a else val[0])
			val[1] = (0 if not acceptat_b else val[1]) 

			# Segons les opcions que accepti el Servidor, tenim tres opcions
			# --- | OACK 	-> alguna opció acceptada
			# --- | DATA 	-> cap opció acceptada
			# --- | ERROR 	-> petició denegada

			if acceptat:
				mida = mida if not acceptat_b else int(pow(2, val[1]))
				serverSocket.sendto(generaOACK(opc, val), addr)

				while nAck != 0 and not fiError:
					ack, addr = serverSocket.recvfrom(4)
					nAck = decodificaACK(ack)
					print(f"Rebent ACK nº {nAck} | Confirmació de RRQ")
				
				text = fd.read(mida)
				serverSocket.sendto(generaDATA(nData, text, mode), addr)

			elif not acceptat and not fiError:
				text = fd.read(mida)
				serverSocket.sendto(generaDATA(nData, text, mode), addr)

			elif fiError:
				pass


		if not fiError:

			while len(text) > 0 and not fiError:

				ack, addr = serverSocket.recvfrom(4)
				nAck = decodificaACK(ack)

				nData = (nAck + 1) % 65536
				serverSocket.sendto(generaDATA(nData, text, mode), addr)

				print(f"rebent ACK nº {nAck} i enviant DATA nº {nData} ... ")								
				if nAnt != nAck:
					text = fd.read(mida)

				nAnt = nAck

			ack, addr = serverSocket.recvfrom(4)
			nAck = decodificaACK(ack)
			
			nData = (nAck + 1) % 65536
			serverSocket.sendto(generaDATA(nData, text, mode), addr)			

			# finalització explícita (len(text) = 0)
			print(f"rebent ACK nº {nAck} i enviant DATA FINAL nº {nData} ...")	
			fd.close()

			print(f"Arxiu {nomFitxer} ENVIAT correctament")
			print("---------------------------------")

	else:
		print("ERROR | Incorrect operation")
