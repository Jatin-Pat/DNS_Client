import sys
import struct
import socket
import time
import random

"""
Contributors:
    Jatin Patel 261114558
    Mathieu Allaire 261119004
"""

"""
The QueryConstructor class is used to create a DNS query message.
"""
class QueryConstructor:
    
    def __init__(self, domaine_name, query_type):
        self.name = domaine_name
        self.query_type = query_type
        self.ID = None
        self.RD = None
        self.QNAME = None
        self.QTYPE = None
        self.QCLASS = None
    
    """
    Create the header of the DNS query message.
    Input:
        None
    Output:
        header - the header section of the DNS query message
    """
    def create_header(self):
        self.ID = random.randint(0, (1 << 16) - 1) # Generate a random 16-bit number for the ID field
        
        QR = 0b0 # 1 bit
        OPCODE = 0b0000 # 4 bits
        AA = 0b0 # 1 bit
        TC = 0b0 # 1 bit
        self.RD = 0b1 # 1 bit
        RA = 0b0 # 1 bit
        Z = 0b000 # 3 bits
        RCODE = 0b0000 # 4 bits
        flags = (QR << 15) | (OPCODE << 11) | (AA << 10) | (TC << 9) | (self.RD << 8) | (RA << 7) | (Z << 4) | RCODE # 16 bits
        
        QDCOUNT = 0b0000000000000001 # 16 bits
        ANCOUNT = 0b0000000000000000 # 16 bits
        NSCOUNT = 0b0000000000000000 # 16 bits
        ARCOUNT = 0b0000000000000000 # 16 bits
        
        header = b''
        header += struct.pack(">HHHHHH", self.ID, flags, QDCOUNT, ANCOUNT, NSCOUNT, ARCOUNT)
        
        return header
    
    """
    Create the question section of the DNS query message.
    Input:
        domaine_name - the domain name
        query_type - the query type
    Output:
        question - the question section of the DNS query message
    """
    def create_question(self, domaine_name, query_type):
        self.QNAME = domaine_name
        domaine_name_list = domaine_name.split(".")
        question = b''
        
        for label in domaine_name_list:
            question += struct.pack(">B", len(label))
            for char in label:
                question += char.encode('ascii')
        question += struct.pack(">B", 0) # end of domain name
        
        self.QTYPE = 0b0000000000001111 if query_type == "-mx" else 0b0000000000000010 if query_type == "-ns" else 0b0000000000000001 # 16 bits
        self.QCLASS = 0b0000000000000001 # 16 bits
        
        question += struct.pack(">HH", self.QTYPE, self.QCLASS)
        
        return question
    
    """
    Wrapper function to create the DNS query message.
    Input:
        None
    Output:
        query - the DNS query message
    """
    def create_query(self):
        header = self.create_header()
        question = self.create_question(self.name, self.query_type)
        return header + question

"""
The QueryHandler class is used to send the DNS query message to the server and process the response.
"""
class QueryHandler:
    
    def __init__(self):
        self.AA = None
        self.QDCOUNT = None
        self.ANCOUNT = None
        self.NSCOUNT = None
        self.ARCOUNT = None
        self.answers = None
        self.authorities = None
        self.additionals = None
    
    """
    Send the DNS query message to the server and receive the response.
    Input: 
        timeout - the time to wait for a response
        max_retries - the maximum number of retries
        port - the port number of the server
        server - the server name
        query - the DNS query message
    Output:
        response - the DNS response message
        elapsed_time - the time taken to receive the response
        retry_count - the number of retries
    """
    def query_server(self, timeout, max_retries, port, server, query):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                send_time = time.time() # time before sending the query
                sock.sendto(query, (server, port))
                response, _ = sock.recvfrom(1024)
                recv_time = time.time() # time after receiving the response
                if response:
                    sock.close()
                    return response, recv_time - send_time, retry_count
                else:
                    retry_count += 1
            except:
                retry_count += 1
            
        print(f"ERROR    Maximum number of retries {max_retries} exceeded")
        sock.close()
        return None
    
    """
    Parse the header of the DNS response message.
    Input:
        query_ID - the ID of the query message
        query_RD - the RD flag of the query message
        response - the DNS response message
    Output:
        None
    """
    def parse_header(self, query_ID, query_RD, response):
        ID = (response[0] << 8) | response[1] 
        flags = (response[2] << 8) | response[3]
        self.QDCOUNT = (response[4] << 8) | response[5]
        self.ANCOUNT = (response[6] << 8) | response[7]
        self.NSCOUNT = (response[8] << 8) | response[9]
        self.ARCOUNT = (response[10] << 8) | response[11]
        
        if ID != query_ID:
            print(f"Error    Unexpected response, the response ID {ID} does not match the query ID {query_ID}")
          
        QR = (flags >> 15) & 0b1
        OPCODE = (flags >> 11) & 0b1111
        self.AA = (flags >> 10) & 0b1
        TC = (flags >> 9) & 0b1
        RD = (flags >> 8) & 0b1
        RA = (flags >> 7) & 0b1
        Z = (flags >> 4) & 0b111
        RCODE = flags & 0b1111
        
        if QR != 1:
            print("Error    Unexpected response, the QR bit does not correspond to a response message")
        elif OPCODE != 0:
            print("Error    Unexpected response, the OPCODE does not correspond to a standard query")
        elif TC != 0:
            print("Error    Unexpected response, message is truncated")
        elif RD != query_RD:
            print(f"Error    Unexpected response, the RD flag {RD} does not match the query RD flag {query_RD}")
        elif Z != 0:
            print("Error    Unexpected response, the Z field is not zero")
        elif RCODE != 0:
            if RCODE == 1:
                print("Error    Unexpected response: the name server was unable to interpret the query")
            elif RCODE == 2:
                print("Error    Unexpected response: the name server was unable to process the query")
            elif RCODE == 3:
                print("Error    Unexpected response: the domain name does not exist")
            elif RCODE == 4:
                print("Error    Unexpected response: the name server does not support the requested query")
            elif RCODE == 5:
                print("Error    Unexpected response: the name server refused to process the query")
    
    """
    Parse the question section of the DNS response message.
    Input:
        query_QNAME - the QNAME of the query message
        query_QTYPE - the QTYPE of the query message
        query_QCLASS - the QCLASS of the query message
        response - the DNS response message
    Output:
        offset - the offset to the next section of the response message
    """      
    def parse_question(self, query_QNAME, query_QTYPE, query_QCLASS, response):
        offset = 12 # start after the header (12 bytes)
    
        QNAME, offset = self.decode_name(response, offset)    
        QTYPES = response[offset] << 8 | response[offset + 1] # 16 bits
        QCLASS = response[offset + 2] << 8 | response[offset + 3] # 16 bits
        
        offset += 4
        
        if query_QNAME != QNAME:
            print(f"Error   Unexpected response, the QNAME {QNAME} does not match the query QNAME {query_QNAME}")
        elif query_QTYPE != QTYPES:
            print(f"Error    Unexpected response, the QTYPE {QTYPES} does not match the query QTYPE {query_QTYPE}")
        elif query_QCLASS != QCLASS:
            print(f"Error    Unexpected response, the QCLASS {QCLASS} does not match the query QCLASS {query_QCLASS}")
        
        return offset
    
    """
    Parse the answer, authority, and additional sections of the DNS response message.
    Input:
        COUNT - the number of records in the section
        offset - the offset to the section
        response - the DNS response message
    Output:
        data - the records in the section
        offset - the offset to the next section
    """
    def parse_answer(self, COUNT, offset, response):
        answers = []

        for i in range(COUNT):
            NAME, offset = self.decode_name(response, offset)
            TYPE = (response[offset] << 8) | response[offset + 1]
            CLASS = (response[offset + 2] << 8) | response[offset + 3]
            TTL = (response[offset + 4] << 24) | (response[offset + 5] << 16) | (response[offset + 6] << 8) | response[offset + 7]
            RDLENGTH = (response[offset + 8] << 8) | response[offset + 9]
            RDATA = []
            PREFERENCE = None
            EXCHANGE = None
            
            offset += 10

            if TYPE == 0b1:
                if RDLENGTH != 4:
                    print(f"ERROR   Unexpected response, the RDLENGTH {RDLENGTH} does not match the expected length for an A record")
                RDATA = response[offset:offset + RDLENGTH]
                offset += RDLENGTH
            elif TYPE == 0b10:
                RDATA, offset = self.decode_name(response, offset)
            elif TYPE == 0b101:
                RDATA, offset = self.decode_name(response, offset)
            elif TYPE == 0b1111:
                PREFERENCE = response[offset] << 8 | response[offset + 1]
                offset += 2
                EXCHANGE, offset = self.decode_name(response, offset)
            
            record = (NAME, TYPE, CLASS, TTL, RDLENGTH, RDATA, PREFERENCE, EXCHANGE)
            answers.append(record)

        return answers, offset
    
    """
    Handle the decoding of the domain name in the DNS response message.
    Input:
        response - the DNS response message
        offset - the offset to the domain name
    Output:
        NAME - the domain name
        offset - the offset past the domain name
    """
    def decode_name(self, response, offset):
        NAME = ""
        compression = False
        offset_with_compression = None

        while response[offset] != 0b0:
            if (response[offset] & 0b11000000) == 0b11000000:
                pointer = ((response[offset] & 0b00111111) << 8) | response[offset + 1]
                if not compression:
                    offset_with_compression = offset + 2  # Save offset
                offset = pointer
                compression = True
            else:
                label_length = response[offset]
                offset += 1
                for i in range(label_length):
                    NAME += chr(response[offset + i])
                NAME += '.'
                offset += label_length

        offset += 1  # Skip the null byte at the end of the name
        if compression:
            offset = offset_with_compression

        return NAME[:-1], offset  # Remove ending dot

    """
    Output the response message.
    Input:
        AA - the AA flag
        COUNT - the number of records in the section
        data - the records in the section
        section_name - the name of the section
    Output:
        None
    """
    def display_response(self, AA, COUNT, data, section_name):
        print(f"*** {section_name} Section ({COUNT} records) ***")
        for record in data:
            NAME, TYPE, CLASS, TTL, RDLENGTH, RDATA, PREFERENCE, EXCHANGE = record
            auth = "auth" if AA else "nonauth"
            
            # A record
            if TYPE == 0b1:
                print(f"IP\t{'.'.join(map(str, RDATA))}\t{TTL}\t{auth}")

            # NS Record
            elif TYPE == 0b10:
                print(f"NS\t{RDATA}\t{TTL}\t{auth}")
                
            # CNAME record
            elif TYPE == 0b101:
                print(f"CNAME\t{RDATA}\t{TTL}\t{auth}")
                
            # MX record
            elif TYPE == 0b1111:
                print(f"MX\t{PREFERENCE}\t{EXCHANGE}\t{TTL}\t{auth}")
    
    """
    Wrapper function to process the DNS response message.
    Input:
        query_ID - the ID of the query message
        query_RD - the RD flag of the query message
        query_QNAME - the QNAME of the query message
        query_QTYPE - the QTYPE of the query message
        query_QCLASS - the QCLASS of the query message
        response - the DNS response message
    Output:
        None
    """    
    def process_response(self, query_ID, query_RD, query_QNAME, query_QTYPE, query_QCLASS, response):
        self.parse_header(query_ID, query_RD, response)
        offset = self.parse_question(query_QNAME, query_QTYPE, query_QCLASS, response)
        self.answers, offset = self.parse_answer(self.ANCOUNT, offset, response)
        self.authorities, offset = self.parse_answer(self.NSCOUNT, offset, response)
        self.additionals, offset = self.parse_answer(self.ARCOUNT, offset, response)
        
        self.display_response(self.AA, self.ANCOUNT, self.answers, "Answer")
        
        if self.ARCOUNT > 0:
            self.display_response(self.AA, self.ARCOUNT, self.additionals, "Additional")

"""
Convert the ASCII domain name to a readable format.
Input:
    data - the ASCII domain name
Output:
    name - the readable domain name
"""
def ascii_to_readable(data):
    name = ""
    offset = 0
    while offset < len(data):
        label_size = data[offset]
        for i in range(label_size):
            name += chr(data[offset + 1 + i])
        name += "."
        offset += label_size + 1
    
    return name[:-1] # remove the last dot

def main():
    # program arguments
    timeout  = 5 # default value
    max_retries = 3 # default value
    port = 53 # default value
    query_type = "A" # default A, other values: MX, NS
    server = None # dns server
    name = None # domain name
    args = sys.argv[1:]
    
    i = 0
    while (i < len(args)):
        if args[i] == "-t":
            timeout = float(args[i+1])
            i += 2
        elif args[i] == "-r":
            max_retries = int(args[i+1])
            i += 2
        elif args[i] == "-p":
            port = int(args[i+1])
            i += 2
        elif args[i] == "-mx" or args[i] == "-ns":
            query_type = args[i]
            i += 1
        elif args[i].startswith("@"):
            server = args[i][1:]
            if (i + 1 >= len(args)):
                print("ERROR    Incorrect input syntax: the domain name must be specified after the server name")
                exit(1)
            name = args[i+1] # domain name
            i += 2
        else:
            print(f"ERROR    Incorrect input syntax: program argument {args[i]} is not recognized")
            exit(1)
    
    if (server is None or name is None):
        print("ERROR    Incorrect input syntax: server name and domain name must be specified")
        exit(1)
    
    print(f"DnsClient sending request for {name}")
    print(f"Server: {server}")
    print(f"Request type: {query_type}")
    
    
    queryConstructor = QueryConstructor(name, query_type)
    dnsQuery = queryConstructor.create_query()
    
    queryHandler = QueryHandler()
    result = queryHandler.query_server(timeout, max_retries, port, server, dnsQuery)
    if result is None:
        exit(1)
    response, elapsed_time, retry_count = result

    print(f"Response received after {elapsed_time} seconds ({retry_count} retries)")
    
    queryHandler.process_response(queryConstructor.ID, queryConstructor.RD, queryConstructor.QNAME, queryConstructor.QTYPE, queryConstructor.QCLASS, response)
              
if __name__ == "__main__":
    main()