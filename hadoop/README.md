# Exercice Hadoop MapReduce

Chaque ligne de `data/donnees.csv` représente un panier de produits séparés par des virgules.

Le Mapper produit les paires de produits du panier. Hadoop regroupe ensuite les valeurs par clef. Le Reducer compte les produits associés, les trie par fréquence décroissante et écrit la liste obtenue.

## Exécution

Les classes Java n'utilisent pas de package. Depuis la racine du dépôt, avec Hadoop disponible dans le terminal :

```powershell
New-Item -ItemType Directory -Force hadoop\build
javac -classpath "$(hadoop classpath)" -d hadoop\build hadoop\src\*.java
jar -cvf hadoop\association-produits.jar -C hadoop\build .

hdfs dfs -mkdir -p /mpmr/input
hdfs dfs -put -f hadoop/data/donnees.csv /mpmr/input/donnees.csv
hdfs dfs -rm -r -f /mpmr/output

hadoop jar hadoop/association-produits.jar MonDriver
hdfs dfs -cat /mpmr/output/part-r-*
```

Le Driver utilise trois reducers. Hadoop peut donc produire jusqu'à trois fichiers `part-r-*`.
