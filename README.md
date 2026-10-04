# FalloutMC Launcher

Launcher Windows 10/11 x64 pour `116.202.116.207:25565`, Minecraft **1.21.1**, NeoForge **21.1.252**, Java **21**. Version de développement **0.1.0**.

## État réel

Les sources du launcher, du menu client, de l'installateur et de la compilation GitHub Actions sont préparées. Le moteur de mise à jour est testé localement. L'exécutable Windows et l'installation complète du jeu doivent être compilés et testés sur Windows. Aucun pack n'est encore publié et aucun fichier n'a été envoyé dans le dépôt par l'assistant.

Les scripts d'export et de préparation ne modifient pas l'installation Minecraft fonctionnelle. Ils n'envoient aucun fichier.

## Première étape : compiler avec GitHub

1. Extraire l'archive des sources dans un dossier.
2. Sur `https://github.com/OYLUR1690/FalloutMC-Launcher`, cliquer **Add file → Upload files**.
3. Glisser tous les fichiers et dossiers à la racine du dossier extrait, **y compris `.github`**. Ne pas glisser un dossier parent qui placerait tout dans un sous-dossier. Ne pas envoyer les fichiers client ni les dossiers `build`, `.gradle`, `dist` ou `__pycache__`.
4. Cliquer **Commit changes** sur la branche `main` (ou `master`).
5. Dans **Actions**, ouvrir **Construire FalloutMC**. Le workflow compile le menu client, teste le moteur et construit sous Windows les deux exécutables et l'installateur. Il ne publie pas de release.
6. Après le succès, télécharger l'artefact **FalloutMC-Windows**. Il contient `FalloutMC-Setup.exe`, `FalloutMC-Launcher.exe`, `FalloutMC-Preparer-Pack.exe`, `falloutmc-menu-0.1.0.jar`.

Si aucun workflow n'apparaît, vérifier que `.github/workflows/build.yml` existe à la racine du dépôt, puis utiliser **Actions → Construire FalloutMC → Run workflow**. En cas d'échec, transmettre le journal du job en échec.

## Récupérer le client fonctionnel

Fermer Minecraft, double-cliquer **Exporter-Client.cmd**, sélectionner le dossier client contenant `mods` et `kubejs`. Le fichier **FalloutMC_fichiers_client.zip** est créé dans le dossier `tools`.

L'export inclut les JAR de `mods`, les assets KubeJS et les scripts client/startup. Il exclut les comptes, mots de passe, mondes, journaux et toute la configuration serveur. Le premier inventaire reçu ne comporte aucun fichier sous `config` ou `defaultconfigs` ; ces dossiers ne sont pas ajoutés implicitement. Les configurations client nécessaires seront sélectionnées ensuite, fichier par fichier.

Cet export est destiné à la préparation locale du pack ; ne pas l'ajouter directement au dépôt public.

## Préparer et publier une version client

La compilation ne suffit pas à rendre le jeu disponible. Un pack client complet doit être publié.

1. Utiliser une copie du client fonctionnel, puis lancer **FalloutMC-Preparer-Pack.exe**.
2. Choisir le dossier client, le mod du menu compilé, l'exécutable launcher compilé, un nom unique tel que `pack-2026.10.04.1`, puis un dossier de sortie vide.
3. Le programme crée `pack.json`, les fichiers `.bin` dont le nom est l'empreinte SHA-256, et `FalloutMC-Launcher.exe`. Les `.bin` correspondent aux fichiers client, dont les JAR. Le manifeste précise leurs chemins réels.
4. Vérifier les licences des mods avant de les republier. Pour un mod distribué uniquement par son auteur, utiliser son URL officielle via la correspondance `--sources` décrite ci-dessous, plutôt qu'un asset republié. Les licences de ce dépôt ne couvrent pas les mods tiers ni Minecraft.
5. Une fois le serveur et le client concordants et testés, créer une release **non brouillon, non préversion**, avec le même tag que celui choisi au point 2. Ajouter tous les fichiers du dossier de sortie, ainsi que `FalloutMC-Setup.exe` pour les nouveaux joueurs.
6. Publier la release comme **Latest**. Ne jamais modifier les fichiers d'une ancienne version : publier un nouveau tag. Les URL du manifeste sont liées au tag immuable ; la dernière release complète indique la version active.

Une modification dans AMP ne publie pas une version client automatiquement. Les changements réservés au serveur ne nécessitent pas de mise à jour client. Pour une modification qui concerne aussi le client, préparer et publier une release complète après la validation serveur. Les joueurs n'ont ensuite rien à copier.

### Configurations et téléchargements officiels

Le préparateur peut aussi être lancé avec Python, ou comme exécutable, avec les mêmes arguments :

```powershell
FalloutMC-Preparer-Pack.exe --client "C:\FalloutMCClient" --menu "C:\Build\falloutmc-menu-0.1.0.jar" --launcher "C:\Build\FalloutMC-Launcher.exe" --tag pack-2026.10.04.1 --output "C:\Publication" --configs "C:\Selection\configs.json" --sources "C:\Selection\sources.json"
```

`configs.json` sélectionne des fichiers individuellement :

```json
[{"path":"config/exemple-client.toml","policy":"initial"}]
```

- `managed` : fichier géré et réparé à chaque lancement, puis supprimé s'il disparaît d'une version future.
- `initial` : installé seulement s'il manque, sans écraser les préférences existantes ; reste présent lorsqu'il est retiré du pack.

`sources.json` associe un chemin de mod à une URL HTTPS de téléchargement officielle de la version exacte. L'empreinte est calculée localement sur le JAR fonctionnel. Aucun inventaire n'est envoyé à une API.

```json
{"mods/exemple.jar":"https://serveur-officiel.example/mod-version-exacte.jar"}
```

## Parcours joueur

Installer **FalloutMC-Setup.exe**, puis ouvrir le raccourci FalloutMC. Aucun Python, Node ou Java à installer soi-même. Saisir son pseudo Minecraft et la RAM du jeu, puis cliquer **Jouer à FalloutMC**.

À chaque clic, le launcher consulte la dernière release et vérifie chaque fichier géré. Il télécharge les fichiers manquants ou modifiés, restaure une transaction interrompue et conserve les anciens fichiers dans les sauvegardes locales. Une erreur réseau ou une empreinte incorrecte bloque le lancement.

Minecraft, ses bibliothèques et son Java 21 proviennent de l'installation officielle prise en charge par `minecraft-launcher-lib`. NeoForge est installé dans la version exacte. Les mods supplémentaires placés manuellement dans cette instance dédiée sont déplacés dans une sauvegarde ; ils ne sont pas chargés avec le pack officiel. Les captures, options et configurations non gérées sont conservées.

Le menu client propose uniquement **Rejoindre FalloutMC**, **Options**, **Quitter**. Le retour au menu principal après une déconnexion revient sur ce menu. Ce menu n'empêche pas quelqu'un d'utiliser un autre launcher : la protection réelle des comptes est EasyLogin côté serveur.

Le pseudo est utilisé avec son UUID hors ligne Minecraft, en respectant les majuscules. Pour **OYLUR**, l'UUID reste `76318c2c-dd5f-3740-9eb1-466b64646470`. En jeu :

```text
/login "mot_de_passe"
/register "mot_de_passe" "mot_de_passe"
```

Le launcher ne demande et ne conserve aucun mot de passe EasyLogin. Il ne crée pas de compte EasyLogin : les joueurs déjà enregistrés utilisent `/login`. Aucun mod d'authentification client n'est ajouté.

## Mise à jour du launcher

`pack.json` contient aussi l'URL et l'empreinte de l'exécutable. Quand une version supérieure est annoncée, le launcher la télécharge, attend sa fermeture, sauvegarde l'ancien exécutable, le remplace et redémarre. Cette fonction doit être validée sur Windows entre deux versions compilées. Pour une nouvelle version du launcher, incrémenter ensemble `launcher/core.py:VERSION`, `installer.iss:AppVersion` et, si le menu change, les versions du mod.

## Données et diagnostics

- Jeu : `%LOCALAPPDATA%\FalloutMC\minecraft`
- Paramètres, journaux et sauvegardes : `%LOCALAPPDATA%\FalloutMC\state`
- Programme : `%LOCALAPPDATA%\Programs\FalloutMC`

Le launcher reste ouvert pendant le jeu et empêche un second lancement simultané. Le journal du jeu peut contenir des messages personnels ; le relire avant de le partager.

La désinstallation du programme conserve l'instance et les préférences du joueur.

## Développement et tests

```text
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python main.py
```

Le mod se compile avec Java 21 et Gradle 8.14.3 : `gradle -p menu-mod build`.

Tests nécessaires avant distribution : installation sur Windows sans Java ni Python, connexion avec un nouveau compte et avec OYLUR migré, menu après déconnexion, réparation d'un fichier, ajout/retrait de mod entre deux releases, coupure de téléchargement, préservation des options et mise à jour de l'exécutable. Les scénarios de fichiers couverts automatiquement sont détaillés dans `VALIDATION.md`.

Sources techniques :
- https://minecraft-launcher-lib.readthedocs.io/en/stable/modules/mod_loader.html
- https://minecraft-launcher-lib.readthedocs.io/en/stable/modules/runtime.html
- https://docs.neoforged.net/docs/1.21.1/gui/screens/
- https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
