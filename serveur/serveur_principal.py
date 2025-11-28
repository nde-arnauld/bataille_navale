import sys
import os
import time

from commun import constantes as const
from serveur.donnees.gestionnaire_utilisateur import GestionnaireUtilisateur
from serveur.reseau.authentification_udp import AuthentificationUDP
from serveur.reseau.ecouteur_serveur import EcouteurServeur
from serveur.logique_jeu.gestionnaire_partie import GestionnairePartie

# Chemin du fichier de sauvegarde
CHEMIN_SAUVEGARDE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    const.FICHIER_SAUVEGARDE_UTILISATEURS
)


class ServeurPrincipal:
    """
    Classe principale orchestrant le lancement et la gestion des composants du serveur.
    """

    def __init__(self):
        print("Initialisation du Serveur Bataille Navale...")

        # 1. Composants de persistance et logique (Instanciés une seule fois)
        self.gestionnaire_utilisateurs = GestionnaireUtilisateur(CHEMIN_SAUVEGARDE)
        self.gestionnaire_partie = GestionnairePartie()

        # 2. Composants réseau
        self.ecouteur_udp: AuthentificationUDP | None = None
        self.ecouteur_tcp: EcouteurServeur | None = None

    def demarrer(self):
        """ Démarre les deux écouteurs (UDP et TCP). """

        # 1. Lancement de l'écouteur UDP (Authentification)
        self.ecouteur_udp = AuthentificationUDP(
            gestionnaire_utilisateurs=self.gestionnaire_utilisateurs,
            port=const.PORT_AUTH
        )
        self.ecouteur_udp.daemon = True
        self.ecouteur_udp.start()

        # 2. Lancement de l'écouteur TCP (Jeu)
        # Injection des dépendances. L'EcouteurServeur est maintenant responsable de
        # gérer et de fournir la map des clients au GestionnairePartie.
        self.ecouteur_tcp = EcouteurServeur(
            gestionnaire_utilisateurs=self.gestionnaire_utilisateurs,
            gestionnaire_partie=self.gestionnaire_partie,  # Injection du GestionnairePartie
            port=const.PORT_JEU
        )
        self.ecouteur_tcp.daemon = True
        self.ecouteur_tcp.start()

        # NOTE: L'étape d'injection de la map est désormais gérée par les callbacks
        # de l'EcouteurServeur, et les méthodes de GestionnairePartie reçoivent
        # la map en argument, respectant le découplage.

        print("-" * 50)
        print("SERVEUR PRÊT.")
        print(f"Auth UDP démarré sur le port {const.PORT_AUTH}.")
        print(f"Jeu TCP démarré sur le port {const.PORT_JEU}.")
        print("Appuyez sur CTRL+C pour arrêter le serveur.")
        print("-" * 50)

        # Boucle principale pour maintenir le thread actif
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.arreter()

    def arreter(self):
        """ Gère l'arrêt propre de tous les threads et sockets. """
        print("\n\nSignal d'arrêt reçu (CTRL+C). Arrêt du serveur...")

        # 1. Arrêter l'écouteur TCP (qui arrêtera aussi tous ses GestionnaireClient)
        if self.ecouteur_tcp:
            self.ecouteur_tcp.stop()
            self.ecouteur_tcp.join()

        # 2. Arrêter l'écouteur UDP
        if self.ecouteur_udp:
            self.ecouteur_udp.stop()
            self.ecouteur_udp.join()

        print("Serveur arrêté avec succès.")
        sys.exit(0)


# --- Point d'entrée du script ---

if __name__ == '__main__':
    server = ServeurPrincipal()
    server.demarrer()