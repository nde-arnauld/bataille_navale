import sys
from reseau import Protocole, Client

def main():
    print("=" * 60)
    print("        BATAILLE NAVALE - CLIENT")
    print("=" * 60)

    # AFFICHER LES RÈGLES
    afficher_regles = input("\nAfficher les règles? (O/N, par défaut N): ").strip().upper()
    if afficher_regles == 'O':
        Protocole.afficher_regles()

    # CONFIGURATION DE LA CONNEXION
    nom = input("\nEntrez votre nom: ").strip()
    if not nom:
        nom = "Joueur"

    host = input("Adresse du serveur (par défaut 127.0.0.1): ").strip()
    if not host:
        host = "127.0.0.1"

    port_str = input("Port (par défaut 5555): ").strip()
    port = int(port_str) if port_str else 5555

    # CHOIX DU MODE DE JEU
    print("\n" + "=" * 60)
    print("MODE DE JEU")
    print("=" * 60)
    print("1. Jouer contre le serveur")
    print("2. Jouer contre un autre joueur")
    print("=" * 60)

    choix_mode = input("Votre choix (1/2, par défaut 1): ").strip()
    mode = Protocole.MODE_VS_JOUEUR if choix_mode == "2" else Protocole.MODE_VS_SERVEUR

    # CHOIX DU MODE DE PLACEMENT DES BATEAUX
    print("\n" + "=" * 60)
    print("MODE DE PLACEMENT DES BATEAUX")
    print("=" * 60)
    print("1. Placement manuel (vous choisissez les positions)")
    print("2. Placement automatique (positions aléatoires)")
    print("=" * 60)

    choix = input("Votre choix (1/2, par défaut 2): ").strip()
    placement_auto = (choix != "1")

    # CRÉER LE CLIENT
    client = Client(host=host, port=port)

    # SE CONNECTER ET JOUER
    try:
        if client.se_connecter(nom, placement_auto=placement_auto, mode=mode):
            client.jouer()
        else:
            print("\n[CLIENT] Impossible de se connecter au serveur")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n[CLIENT] Interruption par l'utilisateur")
        client.deconnecter()
    except Exception as e:
        print(f"\n[CLIENT] Erreur: {e}")
        client.deconnecter()
        sys.exit(1)


if __name__ == "__main__":
    main()