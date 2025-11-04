import json
from .protocole import Protocole

class Message:
    def __init__(self, type_message, donnees=None):
        """
        Initialise un message

        Args:
            type_message: Type du message (selon Protocole)
            donnees: Dictionnaire contenant les données du message
        """
        self.type = type_message
        self.donnees = donnees if donnees is not None else {}

    def serialiser(self):
        """
        Convertit le message en chaîne JSON pour l'envoi sur le réseau

        Returns:
            Chaîne de caractères JSON encodée en bytes
        """
        message_dict = {
            "type": self.type,
            "donnees": self.donnees
        }
        json_str = json.dumps(message_dict)
        return json_str.encode('utf-8')

    @staticmethod
    def deserialiser(data):
        """
        Crée un message à partir de données reçues du réseau

        Args:
            data: Bytes reçus du réseau

        Returns:
            Instance de Message
        """
        try:
            json_str = data.decode('utf-8')
            message_dict = json.loads(json_str)
            return Message(message_dict["type"], message_dict.get("donnees", {}))
        except Exception as e:
            print(f"Erreur lors de la désérialisation: {e}")
            return Message(Protocole.MSG_ERREUR, {"message": "Erreur de désérialisation"})

    def obtenir_type(self):
        """Retourne le type du message"""
        return self.type

    def obtenir_donnees(self):
        """Retourne les données du message"""
        return self.donnees

    def obtenir_donnee(self, cle, valeur_defaut=None):
        """
        Retourne une donnée spécifique

        Args:
            cle: Clé de la donnée
            valeur_defaut: Valeur par défaut si la clé n'existe pas

        Returns:
            La valeur associée à la clé ou valeur_défaut
        """
        return self.donnees.get(cle, valeur_defaut)

    @staticmethod
    def creer_connexion(nom_joueur):
        """Crée un message de connexion"""
        return Message(Protocole.MSG_CONNEXION, {"nom": nom_joueur})

    @staticmethod
    def creer_connexion_ok(message=""):
        """Crée un message de confirmation de connexion"""
        return Message(Protocole.MSG_CONNEXION_OK, {"message": message})

    @staticmethod
    def creer_choix_mode(mode: str):
        """Crée un message pour choisir le mode de jeu"""
        return Message(Protocole.MSG_CHOIX_MODE, {"mode": mode})

    @staticmethod
    def creer_attente_adversaire():
        """Crée un message d'attente d'adversaire"""
        return Message(Protocole.MSG_ATTENTE_ADVERSAIRE, {})

    @staticmethod
    def creer_adversaire_trouve(nom_adversaire: str):
        """Crée un message indiquant qu'un adversaire a été trouvé"""
        return Message(Protocole.MSG_ADVERSAIRE_TROUVE, {"adversaire": nom_adversaire})

    @staticmethod
    def creer_votre_tour():
        """Crée un message indiquant que c'est le tour du joueur"""
        return Message(Protocole.MSG_VOTRE_TOUR, {})

    @staticmethod
    def creer_tour_adversaire():
        """Crée un message indiquant que c'est le tour de l'adversaire"""
        return Message(Protocole.MSG_TOUR_ADVERSAIRE, {})

    @staticmethod
    def creer_placement_bateaux(positions_bateaux):
        """
        Crée un message pour envoyer les positions des bateaux

        Args:
            positions_bateaux: Liste de dict avec les infos de chaque bateau
                               [{"nom": "Porte-avions", "x": 0, "y": 0, "orientation": "H"}, ...]
        """
        return Message(Protocole.MSG_PLACEMENT_BATEAUX, {
            "bateaux": positions_bateaux
        })

    @staticmethod
    def creer_placement_ok():
        """Crée un message de confirmation de placement"""
        return Message(Protocole.MSG_PLACEMENT_OK, {})

    @staticmethod
    def creer_debut_partie():
        """Crée un message de début de partie"""
        return Message(Protocole.MSG_DEBUT_PARTIE, {})

    @staticmethod
    def creer_tir(x, y):
        """Crée un message de tir"""
        return Message(Protocole.MSG_TIR, {"x": x, "y": y})

    @staticmethod
    def creer_reponse_tir(resultat, x, y, bateau_coule=None):
        """Crée un message de réponse à un tir"""
        donnees = {
            "resultat": resultat,
            "x": x,
            "y": y
        }
        if bateau_coule:
            donnees["bateau_coule"] = bateau_coule
        return Message(Protocole.MSG_REPONSE_TIR, donnees)

    @staticmethod
    def creer_fin_partie(gagnant, message=""):
        """Crée un message de fin de partie"""
        return Message(Protocole.MSG_FIN_PARTIE, {
            "gagnant": gagnant,
            "message": message
        })

    @staticmethod
    def creer_abandon():
        """Crée un message d'abandon"""
        return Message(Protocole.MSG_ABANDON, {})

    @staticmethod
    def creer_erreur(message_erreur):
        """Crée un message d'erreur"""
        return Message(Protocole.MSG_ERREUR, {"message": message_erreur})

    def __str__(self):
        """Représentation textuelle du message"""
        return f"Message[{self.type}]: {self.donnees}"