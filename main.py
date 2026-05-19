import discord
from discord import app_commands
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return 'Fila Online!'

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

intents = discord.Intents.default()
intents.message_content = True  # LEMBRETE: Ativar a chavinha "Message Content Intent" no site do Discord!
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Configurações da Fila
fila_jogadores = []
formato_jogadores = {}
valor_fila = 'R$ 2,00'
modo_fila = '1v1 Mobile'

# Controle dos "go" nas salas privadas
salas_ativas = {}

class PainelFila(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def atualizar_embed(self):
        embed = discord.Embed(
            title='Filas | Mobile 📱',
            description='Escolha o seu modo de jogo abaixo para entrar na fila.',
            color=discord.Color.green()
        )
        embed.add_field(name='🏆 Formato', value=modo_fila, inline=False)
        embed.add_field(name='💰 Valor', value=valor_fila, inline=False)
        
        if fila_jogadores:
            lista = '\n'.join([f'{user.mention} | {formato_jogadores[user.id]}' for user in fila_jogadores])
            embed.add_field(name='👑 Jogadores', value=lista, inline=False)
        else:
            embed.add_field(name='👑 Jogadores', value='Nenhum jogador na fila', inline=False)
            
        embed.set_thumbnail(url='https://i.imgur.com/KdfXN7X.png')
        return embed

    async def verificar_fechamento_fila(self, interaction: discord.Interaction):
        global fila_jogadores
        
        if len(fila_jogadores) >= 2:
            p1 = fila_jogadores[0]
            p2 = fila_jogadores[1]
            
            fila_jogadores.clear()
            await interaction.message.edit(embed=self.atualizar_embed())
            
            guild = interaction.guild
            
            # CORRIGIDO: Agora tudo em português certinho
            categoria = discord.utils.get(guild.categories, name='PARTIDAS-PIX')
            if not categoria:
                categoria = await guild.create_category('PARTIDAS-PIX')
                
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                p1: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                p2: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            
            nome_canal = f'x1-{p1.name}-vs-{p2.name}'
            canal_privado = await guild.create_text_channel(name=nome_canal, category=categoria, overwrites=overwrites)
            
            salas_ativas[canal_privado.id] = {
                'jogadores': [p1.id, p2.id],
                'go_dados': set()
            }
            
            embed_sala = discord.Embed(
                title='⚡ Sala Privada Criada!',
                description=f'Confronto definido:\n{p1.mention} **VS** {p2.mention}\n\nPara iniciar a partida, **AMBOS** os jogadores devem digitar exatamente `go` neste chat!',
                color=discord.Color.gold()
            )
            await canal_privado.send(embed=embed_sala)

    @discord.ui.button(label='Gel Infinito', style=discord.ButtonStyle.secondary, emoji='🧊', custom_id='gel_infinito')
    async def gel_infinito(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in fila_jogadores:
            formato_jogadores[interaction.user.id] = 'Gel Infinito'
        else:
            fila_jogadores.append(interaction.user)
            formato_jogadores[interaction.user.id] = 'Gel Infinito'
        await interaction.response.edit_message(embed=self.atualizar_embed())
        await self.verificar_fechamento_fila(interaction)

    @discord.ui.button(label='Gel Normal', style=discord.ButtonStyle.secondary, emoji='🧊', custom_id='gel_normal')
    async def gel_normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in fila_jogadores:
            formato_jogadores[interaction.user.id] = 'Gel Normal'
        else:
            fila_jogadores.append(interaction.user)
            formato_jogadores[interaction.user.id] = 'Gel Normal'
        await interaction.response.edit_message(embed=self.atualizar_embed())
        await self.verificar_fechamento_fila(interaction)

    @discord.ui.button(label='Sair da Fila', style=discord.ButtonStyle.danger, emoji='❌', custom_id='sair_fila')
    async def sair_fila(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in fila_jogadores:
            fila_jogadores.remove(interaction.user)
            formato_jogadores.pop(interaction.user.id, None)
            await interaction.response.edit_message(embed=self.atualizar_embed())
        else:
            await interaction.response.send_message('Você não está em nenhuma fila!', ephemeral=True)

@client.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id in salas_ativas:
        dados_sala = salas_ativas[message.channel.id]
        
        if message.author.id in dados_sala['jogadores'] and message.content.lower().strip() == 'go':
            if message.author.id not in dados_sala['go_dados']:
                dados_sala['go_dados'].add(message.author.id)
                await message.channel.send(f'✅ {message.author.mention} confirmou que está pronto!')
                
            if len(dados_sala['go_dados']) == 2:
                embed_start = discord.Embed(
                    title='🚀 PARTIDA INICIADA!',
                    description='Ambos os jogadores deram **go**!\nPodem criar a sala no jogo e começar o confronto. Boa sorte!',
                    color=discord.Color.red()
                )
                await message.channel.send(embed=embed_start)
                salas_ativas.pop(message.channel.id, None)

@tree.command(name='abrir_fila', description='Inicia o painel de controle da fila de apostas')
@app_commands.describe(valor='Valor da entrada (Ex: R$ 2,00)', modo='Modo de jogo (Ex: 1v1 Mobile)')
async def abrir_fila(interaction: discord.Interaction, valor: str, modo: str):
    global valor_fila, modo_fila
    fila_jogadores.clear()
    formato_jogadores.clear()
    valor_fila = valor
    modo_fila = modo
    
    await interaction.response.send_message('Fila aberta com sucesso!', ephemeral=True)
    view = PainelFila()
    await interaction.channel.send(embed=view.atualizar_embed(), view=view)

@client.event
async def on_ready():
    await tree.sync()
    print(f'SISTEMA DE SALA PRIVADA ONLINE: {client.user}')

keep_alive()

# >>> COLOQUE SEU NOVO TOKEN DO DISCORD AQUI NA ÚLTIMA LINHA <<<
client.run('MTUwNjEzMjgxNzcxMTcyNjY1Mw.Gtq_4S.8gkc-YdQGl5lM8okkz-zeZHLwj5c36s1PukKb8')
          
