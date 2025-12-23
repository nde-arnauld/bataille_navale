# ⚓ Bataille Navale Réseau (M1 Informatique)

## 📝 Description du Projet

Ce projet est une implémentation complète du jeu classique de Bataille Navale (Battleship) dans une architecture **Client-Serveur** modulaire. Développé en Python, il est conçu pour être performant dans un environnement multi-threadé et intègre des fonctionnalités avancées de mise en réseau et de persistance des données, répondant aux exigences du mini-projet de réseau du Master 1 Informatique.

## 🛠️ Spécifications du Projet

### I. Spécifications Fonctionnelles

| Domaine | Fonctionnalité | Description |
| :--- | :--- | :--- |
| **Modes de Jeu** | **Joueur vs Serveur (Solo)** | Le client peut jouer contre le serveur. Le serveur gère la logique de l'adversaire (en tirant aléatoirement). |
| | **Joueur vs Joueur (PvP)** | Les clients jouent les uns contre les autres, le serveur agissant comme arbitre central pour la coordination des tirs. |
| **Session** | **Authentification/Identification** | Le client doit s'identifier (Login/Inscription) avant de pouvoir jouer. |
| | **Reprise de Partie** | Le joueur peut reprendre une partie sauvegardée après une déconnexion et une reconnexion réussie. (uniquement pour une partie solo) |
| **Communication** | **chat Inter-Joueurs** | Les joueurs en mode PvP peuvent échanger des messages via une fonctionnalité de chat intégrée. |
| **Protocole** | **Séquencement des Messages** | Le dialogue client-serveur est structuré par un protocole défini qui gère l'échange de messages (tirs, résultats, changement de tour, fin de partie). |

---

### II. Spécifications Non Fonctionnelles 

| Catégorie | Spécification | Détail Technique |
| :--- | :--- | :--- |
| **Architecture** | **Concurrence** | Le serveur est capable de gérer plusieurs clients simultanément (Multi-threading), assurant l'arbitrage en temps réel. |
| **Réseau** | **Dual-Protocole** | Utilisation de **UDP** pour la phase d'identification rapide. |
| | **Fiabilité du Jeu** | Utilisation de **TCP** pour la session de jeu afin de garantir la fiabilité des données critiques. |
| **Sécurité** | **Sécurité des Mots de Passe** | Les mots de passe sont stockés sous forme hachée pour garantir la sécurité minimale des identifiants utilisateur. |
| **Robustesse** | **Intégrité des Messages** | Le protocole d'échange TCP implémente le mécanisme du *Length-Prefixing* pour garantir la réception complète et non fragmentée des messages JSON. |

---

### III. 🚀 Prochaines Évolutions

Plusieurs fonctionnalités sont prévues pour enrichir l'expérience de jeu et répondre à l'intégralité des extensions possibles :

1.  **Système de Revanche Immédiate :** Possibilité de relancer une nouvelle partie directement après la fin d'une session, que ce soit en mode Solo ou en mode PvP, sans repasser par le menu principal.
2.  **Gestion de Salles de Jeu :** 
    * **Salles Publiques :** Pour un matchmaking automatique simplifié.
    * **Salles Privées :** Permettant à deux amis de se rejoindre via un code de salon spécifique.
3.  **Chronomètre (Timer) :** Intégration d'un temps limite géré par le serveur pour chaque tir afin de dynamiser les parties et d'éviter les blocages en mode PvP.

---

## 🚀 Guide d'Exécution

Pour lancer et tester l'application, suivez les étapes ci-dessous.

### Prérequis

* Python 3.x (recommandé Python 3.9+)

### 1. Lancement du Serveur

Le serveur doit être lancé en premier.

1.  Ouvrez un terminal.
2.  Lancez le script `serveur_principal` (situé dans le package `serveur/`):
    ```bash
    python serveur.serveur_principal
    ```
3.  Le serveur attendra les connexions.

### 2. Lancement des Clients

Pour tester le mode PvP, vous devez lancer au moins deux instances de client.

1.  Ouvrez un **deuxième terminal** (pour le Client 1).
2.  Lancez le script `client_principal` (situé dans le package `client/`):
    ```bash
    python client.client_principal
    ```
3.  Le client vous invitera à vous authentifier et à choisir le mode de jeu.
4.  Pour lancer une partie PvP, ouvrez un **troisième terminal** (pour le Client 2) et répétez les étapes 2 et 3 en utilisant un **nom d'utilisateur différent**.

Dès que le second client choisit le mode PvP, le serveur effectue le matchmaking et la partie démarre.