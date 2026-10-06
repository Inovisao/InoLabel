"""``annotations.coco.json`` como estado do projeto (formato da versão 1.0.0).

O ``.txt`` YOLO de cada frame não guarda ``track_id``, ``source`` nem ``score``; o
COCO guarda tudo e é a base dos scripts de treino. Ele é a fonte da verdade do
projeto: carregado inteiro ao abrir, regravado a cada alteração.

Contrato (igual ao 1.0.0):
- ``categories[].id`` começa em 1 (a API usa índice a partir de 0 internamente);
- ``bbox`` em pixels ``[x, y, largura, altura]``, recortada à imagem;
- ``images[].file_name`` é o caminho relativo ao dataset, com ``/``;
- ``image.id`` e ``annotation.id`` são estáveis entre gravações;
- imagem revisada sem objetos entra em ``images`` sem anotações (negativo).

Módulos: paths (onde fica), builder (memória → COCO), parser (COCO → memória)
e writer (gravação atômica em segundo plano). Sem FastAPI e sem estado global.
"""
