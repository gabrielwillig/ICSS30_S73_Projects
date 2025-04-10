### Avaliação 2 - Arquitetura Orientada a Eventos e Criptografia Assimétrica

__Tutorial RabbitMQ disponível em várias linguagens__:
https://www.rabbitmq.com/tutorials/tutorial-one-python.html
https://www.rabbitmq.com/tutorials/tutorial-one-go.html
https://www.rabbitmq.com/tutorials/tutorial-one-spring-amqp.html
https://www.rabbitmq.com/tutorials/tutorial-one-ruby.html
https://www.rabbitmq.com/tutorials/tutorial-one-php.html
https://www.rabbitmq.com/tutorials/tutorial-one-java.html  
entre outras  
_Obs._: vocês podem estudar apenas os tutoriais 1, 2, 3 e 4.

__Tutorial 1__: Hello World. Conceito básicos: produtor, consumidor, exchange default (sem nome) e fila para armazenar mensagens.

__Tutorial 2__: uma única fila de tarefas para distribuir tarefas entre vários trabalhadores. Cada tarefa é atribuída a um único trabalhador. Exemplifica o uso de confirmações (ack) de mensagens recebidas, persistência de filas e mensagens.

__Tutorial 3__: publish/subscribe - entrega uma mensagem publicada para todos os consumidores utilizando broadcast. Exemplo de sistema de geração de logs, onde consumidores querem receber todas as mensagens de logs e não apenas um subconjunto delas. Explica o uso de uma exchange to tipo fanout para qual os publicadores enviam mensagens. Exchange fanout: entrega todas mensagens para todas as filas que conhece. Explica o binding entre exchange e fila.

__Tutorial 4__: publish/subscribe - consumidores têm interesse apenas em um subconjunto de mensagens. Sistema de geração de logs, onde existem mensagens de log relacionadas à erro, warning e info. Consumidores especificam o tipo de log que desejam receber. Explica o uso da exchange direct, onde uma mensagem é entregue para as filas cuja binding key correspondem exatamente à routing key da mensagem. Uma fila pode ter uma ou mais bindings keys e um mesmo binding key pode estar atrelado a múltiplas filas. 

__Tutorial 5__: registrar interesse de mensagens com base em múltiplos critérios. Uso da exchange topic. Sistemas de geração de logs que permite registrar interesse não apenas em logs com base na sua severidade (info, erro, warning) mas também com base na fonte emissora do log. Uma mensagem enviada para uma exchange topic não podem ter uma routing_key arbitrária, elas deve ser uma lista de palavras (limite de 255 bytes) delimitadas por pontos, as quais especificam alguns recursos ligados à mensagem. A binding key  também deve ter o mesmo formato. A lógica por trás da exchange topic é semelhante à exchange direct, onde uma mensagem enviada com uma routing key específica será entregue a todas as filas vinculadas a uma binding key correspondente. No entanto, existem dois casos especiais importantes para binding key: * pode substituir exatamente uma palavra; # pode substituir zero ou mais palavras. Quando esses caracteres não são utilizados nos bindings, uma exchange topic se comporta como uma exchange direct.

__Tutorial 6__: RPC (Remote Procedure Call) com RabbitMQ, uso de filas de callback. 

__Tutorial 7__: confirmação de publicações.

Criptografia com chaves assimétricas:
https://cryptography.io/en/latest/hazmat/primitives/asymmetric/
https://pycryptodome.readthedocs.io/en/latest/src/signature/pkcs1_v1_5.html
https://docs.oracle.com/javase/tutorial/security/apisign/index.html
https://betterprogramming.pub/exploring-cryptography-in-go-signing-vs-encryption-f19534334ad
https://www.npmjs.com/package/js-crypto-rsa