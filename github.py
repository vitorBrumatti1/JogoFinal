import os
comando_Email = "git config user.email '20241pvai0030020@estudantes.ifpr.edu.br'"
comando2 = "git add *"

mensagem = input("Digite a mensagem de commit: ")
while ( len(mensagem) < 5 ):
    print("⚠️ Mensagem muito pequena, detalhe mais...")
    mensagem = input("Digite a mensagem de commit: ")

comando3 = f"git commit -m \"{mensagem}\" "
comando4 = "git push"

print("... Configurando Email")
os.system(comando_Email)

print("... Adicionando notificações")
os.system(comando2)

print("... Realizando commit")
os.system(comando3)

print("... Fazendo push das alterações")
os.system(comando4)

