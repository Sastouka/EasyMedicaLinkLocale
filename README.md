# EasyMedicaLink

Site de présentation du logiciel de gestion de cabinet et de clinique, édité par **SASTOUKA DIGITAL**. Ce dépôt contient le site statique, pas le serveur de l’application ni une base de données de patients.

- [Site officiel](https://easymedicalink.sastoukadigital.com/)
- [Galerie des interfaces et captures HD](galerie.html)
- [Vidéos de présentation](videos.html)
- [Guide d’utilisation](guide.html)
- [Téléchargements Windows et Android](index.html#telecharger)

## Aperçu local

Depuis la racine du dépôt, lancez `python -m http.server 8000`, puis ouvrez `http://localhost:8000/`. Les vidéos et certains liens s’appuient sur des services externes. Ne placez jamais de fichier de configuration privé ni de donnée patient dans ce dépôt public.

## Organisation

- `index.html` : présentation, modules et téléchargements.
- `module-*.html` : fiches de chaque module.
- `assets/screenshots/` : captures d’interface et aperçus optimisés.
- `css/` et `js/` : présentation et interactions du site.
- `sitemap.xml` : liste des pages publiques référencées.
