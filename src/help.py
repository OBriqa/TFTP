from struct import pack, unpack
from math import log2, pow
import errno, os.path, sys
from socket import *

# codis d'operació dels diferents paquets
opr = {
    "RRQ" : 1,
    "WRQ" : 2,
    "DATA": 3,
    "ACK" : 4,
    "ERR" : 5,
    "OACK": 6
}

# codis d'error i els seus missatges
err = {
    0 : "Not defined, see error message (if any).",
    1 : "File not found.",
    2 : "Access violation.",
    3 : "Disk full or allocation exceeded.",
    4 : "Illegal TFTP operation.",
    5 : "Unknown transfer ID.",
    6 : "File already exists.",
    7 : "No such user."
}

def generaERROR(err, text):

    operacio = pack('BB', 0, opr['ERR'])
    error = pack('BB', 0, err)
    text = bytes(text, 'utf-8')
    zero = pack('B', 0)

    return operacio + error + text + zero

def decodificaERROR(ERR):

    opr = unpack('BB', ERR[0:2])[1]
    msg = (ERR[4:][:-1].split(b'\x00')[0]).decode('utf-8')

    return opr, msg

# Genera una petició {RRQ, WRQ} amb un nomFitxer i un mode i les opcions i valors a negociar
def generaRQM(opr, nomFitxer, mode, opcions, valors):

    opr = pack('BB', 0, opr)
    fitxer = bytes(nomFitxer, 'utf-8')
    zero = pack('B', 0)
    mode = bytes(mode, 'utf-8')

    opc1 = bytes(opcions[0], 'utf-8')
    val1 = pack('B', valors[0])

    opc2 = bytes(opcions[1], 'utf-8')
    val2 = pack('B', valors[1])

    return (opr + fitxer + zero + mode + zero +
            opc1 + zero + val1 + zero  + 
            opc2 + zero + val2 + zero);

# Retorna el tipus de petició, el nom del fitxer, el mode que consta al paquet RQ i les opcions negociades
def decodificaRQM(RQM):

    opr = unpack('BB', RQM[0:2])[1]
    nomFitxer = (RQM[2:][:-1].split(b'\x00')[0]).decode('utf-8')
    mode = (RQM[2:][:-1].split(b'\x00')[1]).decode('utf-8')

    opc1 = (RQM[2:][:-1].split(b'\x00')[2]).decode('utf-8')
    val1 = unpack('B', RQM[2:][:-1].split(b'\x00')[3])[0]

    opc2 = (RQM[2:][:-1].split(b'\x00')[4]).decode('utf-8')
    val2 = unpack('B', RQM[2:][:-1].split(b'\x00')[5])[0]

    return opr, nomFitxer, mode, [opc1, opc2], [val1, val2]
    

# Genera una petició {RRQ, WRQ} amb un nomFitxer i un mode
def generaRQ(opr, nomFitxer, mode):
    
    opr = pack('BB', 0, opr)
    fitxer = bytes(nomFitxer, 'utf-8')
    zero = pack('B', 0)
    mode = bytes(mode, 'utf-8')

    return (opr + fitxer + zero + mode + zero)

# Retorna el tipus de petició, el nom del fitxer i el mode que consta al paquet RQ
def decodificaRQ(RQ):

    opr = unpack('BB', RQ[0:2])[1]
    nomFitxer = (RQ[2:][:-1].split(b'\x00')[0]).decode('utf-8')
    mode = (RQ[2:][:-1].split(b'\x00')[1]).decode('utf-8')

    return opr, nomFitxer, mode

# Genera un paquet OACK amb 'opcions' i 'valors', opcions[i] <-> valors[i]
def generaOACK(opcions, valors):
    
    op = pack('BB', 0, opr['OACK'])
    zero = pack('B', 0)
    
    opc1 = bytes(opcions[0], 'utf-8')
    val1 = pack('B', valors[0])

    opc2 = bytes(opcions[1], 'utf-8')
    val2 = pack('B', valors[1])

    return (op + opc1 + zero + val1 + zero + opc2 + zero + val2 + zero)

# Retorna el codi d'operació del paquet OACK i les opcions negociades amb els seus valors
def decodificaOACK(OACK):
    
    opr = unpack('BB', OACK[0:2])[1]
    
    opc1 = (OACK[2:][:-1].split(b'\x00')[0]).decode('utf-8')
    val1 = unpack('B', OACK[2:][:-1].split(b'\x00')[1])[0]

    opc2 = (OACK[2:][:-1].split(b'\x00')[2]).decode('utf-8')
    val2 = unpack('B', OACK[2:][:-1].split(b'\x00')[3])[0]

    return opr, [opc1, opc2], [val1, val2]


# Genera un packet ACK amb número de bloc 'n'
def generaACK(n):
    return pack('BB', 0, opr['ACK']) + pack('BB', n >> 8, n & 0xff)

# Retorna el número de bloc d'un paquet ACK
def decodificaACK(ACK):
    n = unpack('BB', ACK[2:4])
    return ((n[0] << 8) + n[1])

# Genera un paquet DATA amb número de bloc 'n' i amb 'dades'
def generaDATA(n, dades, mode): # mode

    operacio = pack('BB', 0, opr['DATA'])
    n = pack('BB', n >> 8, n & 0xff)
    dades = bytes(dades, 'utf-8') if mode == 'netASCII' else dades
    
    return (operacio + n + dades)

# Retorna el número de bloc i les dades d'un paquet DATA
def decodificaDATA(DATA):
    n = unpack('BB', DATA[2:4])
    dades = DATA[4:]

    return ((n[0] << 8) + n[1]), dades

# Retorna el codi d'operació del paquet 'PACK'
def opPACK(PACK):
    return unpack('BB', PACK[0:2])[1]
