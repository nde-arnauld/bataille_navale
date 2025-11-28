# Fichier: client_principal.py (Corrigé)

import sys

# Importation de la classe du contrôleur/interface
from client.interface.interface_console import InterfaceConsole


def main():
    """
    Point d'entrée principal du programme client.
    L'adresse du serveur est saisie dans la méthode lancer() de l'InterfaceConsole.
    """
    try:
        # InterfaceConsole est initialisé sans adresse, car elle la demandera elle-même
        client_app = InterfaceConsole(host_serveur="")
        client_app.lancer()

    except Exception as e:
        print(f"Erreur fatale lors de l'exécution du client: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()