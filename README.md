O sistema tem como objetivo melhorar a qualidade de vida dos operadores, resolvendo um problema na hora de solicitar impressão para a Impressora ZQ230 Plus,
metodos convencionais funcionam apartir de um sistema proprio da zebra (Zebra Setup Utilites), mas acaba tendo que ter um certo nivel de experiencia para operar o equipamento ou um outro sistema para poder fazer as funções de impressão e é ai que entra meu sistema.

Link do Zebra: https://www.zebra.com/us/en/support-downloads/software/printer-software/printer-setup-utilities.html?downloadId=3b7879b0-5037-4840-9d6a-b71b6f5c819a#Ta-item-b92208c500-tab

Sendo um sistema bem mais leve e dedicado totalmente a impressão termica da ZQ230 com uso de codigos ZPL, ele atua com o objetivo de facilitar em muito a operação, podendo se limitar o acesso via IP dos equipamentos que tem liberação ao site ou não, ainda se cogita a possibidade de fazer um app..
Atualmente funciona apenas via Navegador em localhost com uma maquina hosteando, mas pretendo muito em breve disponibilizar uma demonstração via AWS, claro para um ambiente de trabalho local funcioan muito bem.

Possiveis complicações:
Cada impressora parece ter vida propria e tem uma margem lateral que você precisa colocar, por isso foi feito uma tela de administrador que libera a possibilidade do Ti de lojas configurar de acordo com sua realidade em loja,
haverá impressoras que necessitem de uma margem -20 ou -120 e atém mesmo com valores positivos, mas na essencia ele permitirá alterar de acordo com a necessidade..

Tela Inicial:

![image](https://github.com/user-attachments/assets/723876c4-ad6d-4e09-9331-cbf7a79fb0d8)

Nesta imagem demonstra o menu principal ao abrir a pagina, o sistema sabe que você tem permissão de acessar e interagir com ele, vem com seleção da etiqueta que atualmente conta com Floricultura e FLV, 
cada etiqueta tem sua configuração, ela funcioan com o codigo EAN e com o codigo reduzido junto com a quantidades de etiqueta.

OBS: Etiqueta de FLV está em andamento, como cada produto tem sua propria descrição de produto como tabela nutricional, estou estudando formas eficazes de cadastrar num banco ou consultar de um existente sem causar absurda redundancia no banco..

![image](https://github.com/user-attachments/assets/55917488-9950-4018-9e46-c88f0137d2a5)

Ao imprimir sempre retornará uma mensagem confirmando a impressão e a quantidade impressa, junto com a loja, toda interaçaõ cria um Log no sistema.

Tela de Login administrativo:

![image](https://github.com/user-attachments/assets/f4a6ebb2-78d7-4ec6-b935-b218da60c7c0)

Haverá um usuario Master sendo o admin do servidor, mas atualmente de forma provisoria sendo: Login admin Senha: 1234

![image](https://github.com/user-attachments/assets/85418ff0-b746-4e4b-b7f4-f46896b298e2)

Após autenticação, o servidor te manterá logado por 5m, ao sair da tela de login ele pedirá senha novamente

No TOP Bar tem algumas telas de acesso, entre elas o cadastro de Impressora.

![image](https://github.com/user-attachments/assets/3e946db1-a256-4804-8de7-69e5d3d39770)

No Cadastro de impressora, a ideia ainda é limitar a visualização ou liberara a interação apenas para o usuario master do servidor, mas a ideia é liberar o cadastro de cada impressora de cada loja de forma individual, podendo ter mais de uma impressora por loja, tendo 1 Por função
no caso as funções atuais que eu conheço hoje são: FLV, Padaria e Floricultura e há lojas com 2-4 Impressoras que podem ser dedicadas ou não ao trabalho.

E pro fim a tela de Logs que ainda estou trabalhando, mas a ideia é registrar o que foi solicitado dentro do sistema, cada interação..

![image](https://github.com/user-attachments/assets/7a92e6b7-8da4-437e-9238-56475abf2ce5)



