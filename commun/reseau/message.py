import json
from ..constantes import *
from typing import Any


class Message:
    def __init__(self, type_message: str, donnees: dict[str, Any] | None = None):
        """
        Initialise un message
        """
        self.type = type_message
        self.donnees = donnees if donnees is not None else {}

    def serialiser(self) -> bytes:
        """
        Convertit le message en chaîne JSON pour l'envoi sur le réseau
        """
        message_dict = {
            "type": self.type,
            "donnees": self.donnees
        }
        json_str = json.dumps(message_dict)

        return json_str.encode(ENCODAGE)

    @staticmethod
    def deserialiser(data: bytes) -> 'Message':
        """
        Crée un message à partir de données reçues du réseau
        """
        try:
            # Utilisation de l'encodage défini dans les constantes
            json_str = data.decode(ENCODAGE)
            message_dict = json.loads(json_str)

            if "type" not in message_dict:
                # Le message doit contenir un type
                raise ValueError("Message JSON sans clé 'type'.")

            return Message(message_dict["type"], message_dict.get("donnees", {}))

        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as e:
            print(f"Erreur lors de la désérialisation: {e}")
            return Message(MSG_ERREUR, {"message": "Données corrompues ou format invalide"})

    def obtenir_type(self) -> str:
        return self.type

    def obtenir_donnees(self) -> dict[str, Any]:
        return self.donnees

    def obtenir_donnee(self, cle: str, valeur_defaut: Any = None) -> Any:
        return self.donnees.get(cle, valeur_defaut)

    @staticmethod
    def creer_connexion(nom_joueur: str):
        return Message(MSG_CONNEXION, {"nom": nom_joueur})

    @staticmethod
    def creer_connexion_ok(message: str = ""):
        return Message(MSG_CONNEXION_OK, {"message": message})

    @staticmethod
    def creer_choix_mode(mode: str):
        return Message(MSG_CHOIX_MODE, {"mode": mode})

    # Messages d'Authentification (UDP)
    @staticmethod
    def creer_auth_login(nom: str, mdp: str):
        """Crée un message de tentative de connexion/login (UDP)"""
        return Message(MSG_AUTH_LOGIN, {"nom": nom, "mdp": mdp})

    @staticmethod
    def creer_auth_register(nom: str, mdp: str):
        """Crée un message de demande d'inscription/register (UDP)"""
        return Message(MSG_AUTH_REGISTER, {"nom": nom, "mdp": mdp})

    # NOUVEAU: Messages de Sauvegarde/Reprise
    @staticmethod
    def creer_reprendre_partie():
        """Commande du client pour reprendre une partie sauvegardée"""
        return Message(MSG_REPRENDRE_PARTIE, {})

    @staticmethod
    def creer_nouvelle_partie():
        """Commande du client pour commencer une nouvelle partie (supprimer l'ancienne sauvegarde)"""
        return Message(MSG_NOUVELLE_PARTIE, {})

    @staticmethod
    def creer_sauvegarder_partie():
        """Commande du client pour demander la sauvegarde de la partie en cours"""
        return Message(MSG_SAUVEGARDER_PARTIE, {})

    # Message de Chat
    @staticmethod
    def creer_chat(message: str):
        """Crée un message de chat à envoyer à l'adversaire/serveur"""
        return Message(MSG_CHAT, {"message": message})

    @staticmethod
    def creer_attente_adversaire():
        return Message(MSG_ATTENTE_ADVERSAIRE, {})

    @staticmethod
    def creer_adversaire_trouve(nom_adversaire: str):
        return Message(MSG_ADVERSAIRE_TROUVE, {"adversaire": nom_adversaire})

    @staticmethod
    def creer_votre_tour():
        return Message(MSG_VOTRE_TOUR, {})

    @staticmethod
    def creer_tour_adversaire():
        return Message(MSG_TOUR_ADVERSAIRE, {})

    @staticmethod
    def creer_placement_navires(positions_navires: list[dict[str, Any]]):
        return Message(MSG_PLACEMENT_NAVIRES, {"navires": positions_navires})

    @staticmethod
    def creer_placement_ok():
        return Message(MSG_PLACEMENT_OK, {})

    @staticmethod
    def creer_debut_partie(nom_joueur: str=None, mode: str=None):
        donnees = {}
        if nom_joueur:
            donnees["adversaire"] = nom_joueur
        if mode:
            donnees["mode"] = mode
        return Message(MSG_DEBUT_PARTIE, donnees)

    @staticmethod
    def creer_message_reprise(msg_reprise_data: dict[str, Any]):
        return Message(MSG_PARTIE_REPRISE, msg_reprise_data)

    @staticmethod
    def creer_tir(x: int, y: int):
        return Message(MSG_TIR, {"x": x, "y": y})

    @staticmethod
    def creer_reponse_tir(resultat: str, x: int, y: int, bateau_coule: str | None = None):
        donnees = {"resultat": resultat, "x": x, "y": y}
        if bateau_coule:
            donnees["bateau_coule"] = bateau_coule
        return Message(MSG_REPONSE_TIR, donnees)

    @staticmethod
    def creer_reponse_tir_recu(resultat: str, x: int, y: int, tireur: str, bateau_coule: str | None = None):
        donnees = {"resultat": resultat, "x": x, "y": y, "adversaire": tireur}
        if bateau_coule:
            donnees["bateau_coule"] = bateau_coule
        return Message(MSG_REPONSE_TIR_RECU, donnees)

    @staticmethod
    def creer_fin_partie(gagnant: str, message: str = ""):
        return Message(MSG_FIN_PARTIE, {"gagnant": gagnant, "message": message})

    @staticmethod
    def creer_abandon():
        return Message(MSG_ABANDON, {})

    @staticmethod
    def creer_erreur(message_erreur: str):
        return Message(MSG_ERREUR, {"message": message_erreur})

    def __str__(self):
        return f"Message[{self.type}]: {self.donnees}"