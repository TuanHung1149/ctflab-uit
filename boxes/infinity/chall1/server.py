import socket
import random

PORT = 7171
FLAG = "INF01{XXXXXXXX}"

# Create a socket object
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the socket to a specific address and port
server_socket.bind(("0.0.0.0", PORT))

# Listen for incoming connections
server_socket.listen(0)

print(f"Server is listening on port {PORT}...")

# Predefined number to compare with
def genTest():
    num1 = random.randint(1, 100)
    num2 = random.randint(1, 100)
    return num1+num2, num1, num2

while True:
    # Accept a connection from a client
    client_socket, client_address = server_socket.accept()
    print(f"Accepted connection from {client_address}")

    # Set a timeout of 10 seconds for receiving a message
    client_socket.settimeout(10)

    try:
        # generate test
        result, num1, num2 = genTest()
        # Send a "hello world!" message to the client
        client_socket.send("[infinity.insec] Bot checking!!!".encode("utf-8"))
        client_socket.send(f"[infinity.insec] What is the sum of {num1} and {num2}?: ".encode("utf-8"))

        # Receive a message from the client
        client_message = client_socket.recv(32).decode("utf-8")
        print(f"Client message: {client_message}")
        print(f"True result: {result}")
        # Compare the received message with the result
        if client_message == f"{result}\n" or client_message == f"{result}\r\n":
            response = f"[infinity.insec] Wellcome user. Here is your flag: {FLAG}"
        else:
            response = "[infinity.insec] You are a dumb bot!!!"

        # Send the response to the client
        client_socket.send(response.encode("utf-8"))

    except socket.timeout:
        # Handle the timeout scenario
        response = "\r\n[infinity.insec] Timeout."
        client_socket.send(response.encode("utf-8"))
    except ConnectionResetError:
        # Handle client disconnect
        pass
    except Exception as e:
        print(e)
    finally:
        # Close the client socket
        client_socket.close()
