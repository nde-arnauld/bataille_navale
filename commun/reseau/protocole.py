import socket
from .message import Message
from ..constantes import TAILLE_ENTETE

class Protocole:
    """
    Gère l'encapsulation des messages avec un préfixe de taille
    pour garantir l'intégrité des données sur le flux TCP.
    """

    @staticmethod
    def recevoir_message(socket_actif: socket.socket, entity: str) -> bytes | None:
        """
        Reçoit un message complet du socket en lisant d'abord l'entête de taille.
        """
        try:
            # 1. Recevoir l'entête de taille (4 bytes)
            taille_data = socket_actif.recv(TAILLE_ENTETE)

            # Si le socket est fermé ou vide, on retourne None
            if not taille_data:
                return None

            # 2. Décodage de la taille (big-endian pour l'ordre des octets)
            taille = int.from_bytes(taille_data, byteorder='big')

            # 3. Recevoir le message complet
            data = b''
            bytes_recus = 0

            while bytes_recus < taille:
                # Recevoir le paquet restant
                paquet_manquant = taille - bytes_recus
                paquet = socket_actif.recv(paquet_manquant)

                # Si le paquet est vide, le client s'est déconnecté prématurément
                if not paquet:
                    print(f"[{entity}] Erreur de réception: Fin de flux prématurée.")
                    return None

                data += paquet
                bytes_recus += len(paquet)

            return data

        except Exception as e:
            # Gérer les erreurs de socket (timeout, connexion reset)
            print(f"[{entity}] Erreur de réception: {e}")
            return None

    @staticmethod
    def envoyer_message(socket_actif: socket.socket, message: Message, entity: str) -> bool:
        """
        Envoie un message sur le socket en utilisant le protocole d'entête de taille.
        """
        try:
            data = message.serialiser()
            taille = len(data)

            # 1. Envoyer d'abord la taille (4 bytes, big-endian)
            taille_bytes = taille.to_bytes(TAILLE_ENTETE, byteorder='big')
            socket_actif.sendall(taille_bytes)

            # 2. Envoyer le message
            socket_actif.sendall(data)

            return True

        except Exception as e:
            print(f"[{entity}] Erreur d'envoi: {e}")
            return False