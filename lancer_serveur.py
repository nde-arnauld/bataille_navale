import sys
from reseau.serveur import Serveur


def main():
    print("=" * 60)
    print("        SERVEUR DE BATAILLE NAVALE")
    print("=" * 60)

    # Configuration du serveur
    host = input("Adresse d'écoute (par défaut 0.0.0.0): ").strip() or "0.0.0.0"
    port_str = input("Port (par défaut 5555): ").strip()
    port = int(port_str) if port_str else 5555

    # Créer et démarrer le serveur
    serveur = Serveur(host=host, port=port)

    try:
        serveur.demarrer()
    except KeyboardInterrupt:
        print("\n[SERVEUR] Interruption par l'utilisateur")
        serveur.arreter()
    except Exception as e:
        print(f"\n[SERVEUR] Erreur: {e}")
        serveur.arreter()
        sys.exit(1)


if __name__ == "__main__":
    main()