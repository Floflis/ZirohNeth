# 🌈 ZirohNeth — Architecture TODOs, riscos e lições do ZeroNet

> **Status:** documento de planejamento, não especificação final nem implementação existente.  
> **Data da revisão:** 17/11/2026  
> **Objetivo:** projetar uma rede social P2P que aprenda com ZeroNet/ZeroMe sem reconstruir seus gargalos sob nomes novos.

---

## 🌈 0. Princípios que não podem ser negociados

- [ ] **Nenhum Hub obrigatório.** Uma pessoa não deve precisar escolher um servidor/hub para que sua identidade, perfil ou publicações existam.
- [ ] **Nenhum banco global obrigatório.** Não criar um único banco OrbitDB para todos os usuários, posts ou comentários.
- [ ] **Identidade separada dos dados.** A identidade deve continuar verificável mesmo que um peer, indexador, relay ou serviço de pinning desapareça.
- [ ] **Dados portáveis.** Uma pessoa deve conseguir migrar seus dados e referências para outro dispositivo ou implementação sem pedir autorização a um operador.
- [ ] **Distribuição explícita.** Todo tipo de dado precisa ter política documentada de replicação, retenção, descoberta e recuperação.
- [ ] **Local-first.** A aplicação deve continuar útil com conectividade intermitente e sincronizar depois, sem prometer consistência instantânea global.
- [ ] **Sem blockchain como banco social.** Ethereum serve à identidade, à autorização, à coordenação e a compromissos verificáveis. Não deve receber cada curtida, comentário ou publicação.
- [ ] **Nenhuma tecnologia é considerada escalável por reputação.** Cada escolha precisa passar por testes de carga, recuperação e operação real.

## 🌈 1. O que aprender com ZeroNet e ZeroMe

### 🌈 1.1 O que funcionava

- O modelo de conteúdo endereçado/assinado permitia verificar a origem e a integridade de atualizações.
- A distribuição P2P reduzia a dependência de um único servidor de hospedagem.
- A replicação local tornava possível consultar conteúdo já obtido mesmo sem conexão.
- Os Hubs do ZeroMe dividiram a carga social entre diferentes espaços de armazenamento.

### 🌈 1.2 O que não devemos reproduzir

- [ ] **Não trocar Hubs por bancos gigantes.** Um único OrbitDB com a rede inteira apenas muda o nome do gargalo.
- [ ] **Não confundir distribuição com escalabilidade.** Ter muitos peers não garante que os dados estejam particionados de forma eficiente.
- [ ] **Não replicar tudo para todo mundo.** O cliente deve sincronizar somente os dados necessários às suas escolhas e políticas locais.
- [ ] **Não transformar um índice em novo ponto central.** Busca, descoberta e feed precisam tolerar múltiplos indexadores e reconstrução local.
- [ ] **Não criar um único peer popular obrigatório.** Usuários muito seguidos, comunidades grandes e relays precisam de estratégias para hotspots.
- [ ] **Não tratar conteúdo social como site estático.** Posts, comentários, reações e relações sociais têm padrões de escrita e leitura diferentes de arquivos de um site.
- [ ] **Não pressupor que CRDT resolve semântica social.** CRDT ajuda a reconciliar alterações concorrentes; não decide quem pode publicar, o que é spam, qual edição prevalece por regra de produto ou como moderar conteúdo.
- [ ] **Não presumir que assinatura significa privacidade.** Assinaturas provam autoria/integridade; não escondem conteúdo nem metadados.
- [ ] **Não tornar a participação dependente de um operador de Hub.** Relays, indexadores, gateways e pinning devem ser serviços substituíveis, não autoridades sobre a identidade.

### 🌈 1.3 Cuidado especial com o ZeroMe

- [ ] Documentar o modelo real de Hubs/MergerSites e o caminho de leitura do feed antes de usá-lo como baseline técnico.
- [ ] Verificar separadamente o estado do cliente ZeroNet, do ZeroMe e dos forks. A atividade de um repositório não prova que toda a rede ou todos os Zites estejam saudáveis.
- [ ] Não assumir que o fork `zeronet-conservancy/0me` recebeu manutenção recente: a listagem pública consultada indicava atualização em 20/11/2022.

## 🌈 2. Arquitetura candidata

Esta é uma **proposta para prototipagem**. Os componentes e suas versões ainda precisam ser confirmados e fixados no início da implementação.

| Área | Candidato | Responsabilidade | Não deve ser usado para |
|---|---|---|---|
| Identidade e confiança | Ethereum + assinaturas | Identidade verificável, autorização, ownership e âncoras opcionais | Guardar o feed inteiro on-chain |
| Dados sociais | OrbitDB (`@orbitdb/core`) | Logs e bancos P2P por usuário/comunidade/domínio | Um banco global replicado por todos |
| Conteúdo | IPFS via Helia | Blocos endereçados por CID para mídia e anexos | Garantir sozinho retenção eterna |
| Rede P2P | Libp2p | Conexão, descoberta, transporte e sincronização | Ser confundido com armazenamento durável |
| Feed | Índice local + indexadores substituíveis | Agregar e ordenar o conteúdo que cada pessoa escolheu acompanhar | Ser a fonte autoritativa de identidade ou publicações |
| Persistência | Blockstore/datastore persistentes + pinning | Manter blocos e estado após reinicialização | Depender apenas de memória ou de um único pinning provider |

### 🌈 2.1 Particionamento inicial a testar

- [ ] **Profile DB:** dados mutáveis e pequenos do perfil, com política clara de histórico.
- [ ] **Posts DB:** log de publicações de uma identidade, com paginação e limites definidos.
- [ ] **Social Graph DB:** relações de seguir/deixar de seguir, bloqueios e listas, separadas de conteúdo público.
- [ ] **Community DB:** dados de uma comunidade, com permissões e regras próprias.
- [ ] **Discussion/Comments DB:** comentários e respostas, particionados por conversa ou comunidade quando isso reduzir fan-out.
- [ ] **Media:** arquivos grandes no IPFS; bancos sociais guardam referências CID e metadados mínimos.
- [ ] Definir limites de tamanho, retenção, histórico e replicação para cada banco antes de liberar criação ilimitada.

**Importante:** não assumir que um banco por pessoa é sempre suficiente. Uma conta muito ativa pode precisar de segmentação temporal ou por coleção; comunidades gigantes podem precisar de subpartições. A decisão deve vir de benchmark, não de preferência estética.

## 🌈 3. TODOs por fase

### 🌈 Fase 0 — Pesquisa, decisões e threat model

- [ ] Comparar versões atuais e maturidade de OrbitDB, Helia, Libp2p e bibliotecas Ethereum antes de escolher dependências.
- [ ] Escrever ADRs (*Architecture Decision Records*) para cada decisão estrutural importante.
- [ ] Definir o que significa “descentralizado” em cada recurso: identidade, publicação, busca, entrega, moderação, recuperação e governança.
- [ ] Criar um threat model: peer malicioso, Sybil, spam, eclipse, censura por indexador, roubo de chave, perda de dispositivo, replay e indisponibilidade de conteúdo.
- [ ] Definir metas mensuráveis de latência, consumo de disco, tráfego, tempo de bootstrap e recuperação. Não inventar números antes de medir um protótipo.
- [ ] Mapear requisitos legais e de privacidade relacionados a dados pessoais, retenção e exclusão.

### 🌈 Fase 1 — Identidade e autorização

- [ ] Definir formato de identidade independente de um único provedor Ethereum.
- [ ] Separar **identificador**, **chave de assinatura**, **chave de criptografia** e **permissões**. Não usar uma única chave para tudo.
- [ ] Definir rotação de chaves, recuperação, revogação e migração para uma nova chave.
- [ ] Assinar eventos com domínio/contexto, versão, nonce ou sequência, timestamp quando necessário e identificador da aplicação.
- [ ] Implementar proteção contra replay e validação de autoria antes de aceitar eventos.
- [ ] Definir como serão tratadas múltiplas carteiras, contas smart-wallet e identidades sem transação on-chain.
- [ ] Avaliar ENS como nome legível opcional, não como requisito de disponibilidade da identidade.
- [ ] Definir permissões de escrita/leitura em cada tipo de banco OrbitDB.
- [ ] Testar recuperação da conta em dispositivo novo sem confiar em um servidor central.

### 🌈 Fase 2 — Conteúdo e armazenamento

- [ ] Implementar Helia com **blockstore persistente** e datastore persistente no ambiente de produção.
- [ ] Nunca usar configuração de memória como padrão silencioso para dados que a usuária espera manter após reiniciar.
- [ ] Testar persistência após fechar processo, reiniciar dispositivo, atualizar aplicação e recuperar backup.
- [ ] Definir política de pinning local e redundância remota; registrar quem mantém cada cópia e como auditar disponibilidade.
- [ ] Criar verificação periódica de blocos e reparo/re-replicação quando uma cópia desaparecer.
- [ ] Separar conteúdo público, privado e conteúdo criptografado antes do upload.
- [ ] Definir limites de tamanho, streaming e upload retomável para mídia grande.
- [ ] Documentar o comportamento de garbage collection e garantir que blocos necessários estejam pinados antes de coletar lixo.
- [ ] Definir política de remoção: apagar referência, remover pins controlados e explicar que cópias já replicadas podem continuar existindo.
- [ ] **CID e hash:** testar interoperabilidade dos algoritmos escolhidos em todos os clientes. Helia não deve ser presumido compatível com qualquer multihash sem configurar o hasher correspondente.
- [ ] Se for adotado CIDv1 + BLAKE3 (incluindo saída de 512 bits), criar testes cruzados de criação, parsing, recuperação e validação do CID em implementações diferentes antes de padronizar.

### 🌈 Fase 3 — Modelo social e OrbitDB

- [ ] Prototipar Profile DB, Posts DB e Social Graph DB separadamente.
- [ ] Selecionar tipos de banco OrbitDB de acordo com o padrão de acesso; não escolher um tipo apenas porque é o mais simples de demonstrar.
- [ ] Definir esquema/versionamento de eventos e migrações compatíveis.
- [ ] Estabelecer limites de tamanho/idade por partição e estratégia para arquivar ou segmentar bancos que cresçam demais.
- [ ] Definir como seguir uma conta sem replicar todo o histórico desde o primeiro dia.
- [ ] Definir bootstrap de estado: snapshot verificável, cursor/offset e replay incremental de eventos.
- [ ] Testar duas ou mais escritoras offline criando alterações concorrentes.
- [ ] Definir regras determinísticas para exclusões, edições, moderação e conflitos que não sejam resolvidos apenas pelo CRDT.
- [ ] Garantir que a autorização seja validada por cada peer, e não apenas pela interface que criou o evento.
- [ ] Documentar limites e comportamento de PubSub, descoberta e sincronização; PubSub não deve ser tratado como fila durável de mensagens.

### 🌈 Fase 4 — Feed, busca e descoberta

- [ ] Construir feed local a partir das contas e comunidades que a pessoa escolheu acompanhar.
- [ ] Guardar cursores por origem para evitar baixar ou processar o mesmo evento repetidamente.
- [ ] Definir ordenação estável quando relógios dos dispositivos estiverem incorretos ou divergentes.
- [ ] Tratar eventos atrasados, duplicados e fora de ordem.
- [ ] Fazer indexadores independentes e substituíveis; permitir reconstruir o índice a partir dos eventos válidos.
- [ ] Definir descoberta de identidade sem uma lista central obrigatória.
- [ ] Evitar consultas globais que exijam rastrear cada publicação de toda a rede.
- [ ] Criar filtros locais de idioma, conteúdo, contas bloqueadas, comunidades e preferências.
- [ ] Testar cold start: uma usuária recém-chegada precisa construir seu feed sem baixar a rede inteira.

### 🌈 Fase 5 — Ethereum e contratos

- [ ] Manter operações sociais comuns fora da L1: posts, comentários, curtidas e follows não devem exigir transação Ethereum individual.
- [ ] Usar a cadeia para o mínimo necessário: registros, compromissos/raízes, ownership, recuperação ou governança quando houver benefício demonstrável.
- [ ] Avaliar L2 antes de desenhar qualquer fluxo de alta frequência on-chain.
- [ ] Separar evento de contrato, estado de contrato e dados off-chain. Eventos Ethereum não são automaticamente consultáveis por contratos e não substituem armazenamento de dados.
- [ ] Não assumir que uma referência/CID on-chain garante que o conteúdo continue disponível.
- [ ] Avaliar taxas, UX, disponibilidade de RPC, reorgs, finalização e comportamento em troca de rede.
- [ ] Não fazer a identidade depender de um único RPC, indexador ou frontend de carteira.
- [ ] Publicar contratos somente após threat model, testes, revisão e plano de atualização/imutabilidade.

### 🌈 Fase 6 — Resiliência, abuso e operação

- [ ] Criar métricas de replicação, peers disponíveis, falhas de fetch, tamanho do armazenamento e atraso de sincronização.
- [ ] Fazer peers de bootstrap e relays substituíveis; distribuir múltiplas opções sem torná-las autoridades.
- [ ] Criar mecanismos antispam com custos proporcionais e configuráveis; evitar exigir pagamento para cada ação social.
- [ ] Projetar bloqueio, denúncia, moderação comunitária e filtros locais sem apagar a possibilidade de clientes independentes.
- [ ] Criptografar dados privados no cliente antes de armazená-los/distribuí-los.
- [ ] Evitar publicar no IPFS dados pessoais que a usuária espera conseguir apagar depois.
- [ ] Documentar o que metadados de rede revelam: IPs, horários, relações, tamanhos e padrões de acesso.
- [ ] Criar backups exportáveis e teste de restauração real.
- [ ] Testar perda total de um peer, de um pinning provider e de um indexador.

### 🌈 Fase 7 — Testes de escala antes de declarar vitória

- [ ] Simular muitos usuários pequenos, poucos usuários extremamente ativos e comunidades com alto volume.
- [ ] Medir bytes baixados por usuário novo, por seguidor e por publicação.
- [ ] Medir custo de armazenamento por mês e crescimento do estado local.
- [ ] Medir p50/p95 de abertura do feed, publicação, descoberta e recuperação.
- [ ] Testar feed com milhares de origens sem sincronizar cada banco integralmente.
- [ ] Testar dispositivo móvel com armazenamento limitado, bateria limitada e conexão intermitente.
- [ ] Testar partições de rede prolongadas e reconciliação posterior.
- [ ] Testar comportamento com clocks errados, duplicatas, mensagens atrasadas e eventos inválidos.
- [ ] Testar popularidade extrema sem transformar a autora em servidor obrigatório.
- [ ] Publicar resultados e limites conhecidos. Nunca declarar “escala infinita”.

## 🌈 4. Erros arquiteturais a evitar

| Anti-pattern | Por que é perigoso | Regra para ZirohNeth |
|---|---|---|
| Um OrbitDB global | Recria um domínio de replicação enorme | Particionar por identidade, comunidade, conversa ou período |
| Um Hub obrigatório | Introduz dependência operacional e possível ponto de censura | Relays e indexadores opcionais e substituíveis |
| Replicação total | Tráfego e disco crescem com toda a rede | Replicação seletiva, cursores e limites |
| Feed global central | Índice vira autoridade e gargalo | Agregação local e indexadores reconstruíveis |
| Tudo on-chain | Custo, latência e dependência da cadeia | Ethereum apenas para confiança/coordenação necessária |
| CID sem pinning | Endereço existe, conteúdo pode não estar disponível | Política explícita de retenção e redundância |
| Helia em memória em produção | Blocos e identidade local podem desaparecer no encerramento | Blockstore e datastore persistentes |
| CRDT como solução de produto | Merge não resolve autorização, spam ou semântica | Regras determinísticas por tipo de evento |
| Chave única para tudo | Comprometimento tem impacto amplo | Separar signing, encryption, recovery e permissions |
| Descoberta central obrigatória | Censura/indisponibilidade de um diretório afeta a rede | Múltiplas fontes e protocolos de descoberta |
| “Descentralizado” sem teste | Pode esconder dependências centralizadas | Mapear e testar todos os pontos de confiança |
| Exclusão prometida no IPFS | Cópias replicadas podem persistir | Explicar limites e não publicar segredo em claro |

## 🌈 5. Checklist de revisão para cada PR

Antes de aceitar uma mudança de arquitetura, responder:

- [ ] Qual dado está sendo criado/modificado e quem é sua autoridade?
- [ ] Onde ele fica armazenado? O armazenamento sobrevive a um restart?
- [ ] Quem replica esse dado e por quê?
- [ ] É possível recuperar o dado se o peer original ficar offline?
- [ ] A mudança cria uma dependência de Hub, gateway, RPC, indexador ou serviço único?
- [ ] Como o sistema se comporta com eventos duplicados, atrasados ou concorrentes?
- [ ] A assinatura é validada? Existe proteção contra replay?
- [ ] A mudança vaza dados pessoais ou metadados novos?
- [ ] Qual é o custo em bytes, disco, CPU, bateria e transações?
- [ ] Existe teste automatizado para falha, reinício e perda de peer?
- [ ] A documentação e o TODO foram atualizados?

## 🌈 6. Decisões ainda abertas

- [ ] OrbitDB será a camada social principal ou apenas uma implementação inicial/prototípica?
- [ ] Qual estratégia de particionamento será adotada para contas muito ativas?
- [ ] Como snapshots e checkpoints serão autenticados e distribuídos?
- [ ] Como será feita a descoberta inicial de peers e bancos sem diretório central obrigatório?
- [ ] Quais dados serão públicos por padrão e quais exigirão criptografia ponta a ponta?
- [ ] Como serão feitas recuperação de identidade e rotação de chaves?
- [ ] Ethereum L1, L2, múltiplas redes ou suporte agnóstico a cadeia?
- [ ] Qual será a política de retenção e redundância para mídia?
- [ ] Quais clientes e plataformas serão suportados primeiro?
- [ ] Qual formato de exportação/importação permitirá migrar dados entre implementações?

## 🌈 7. Referências e estado observado do ZeroNet

**Nota:** datas abaixo são o estado público observado na pesquisa de 17/11/2026. “Atualizado por último” não é sinônimo de manutenção saudável, releases regulares ou segurança auditada. Também não prova que não exista outro fork pessoal com commits posteriores.

| Projeto | Observação pública encontrada | Link |
|---|---|---|
| ZeroNet original | Último push público observado em 31/01/2024 | [HelloZeroNet/ZeroNet](https://github.com/HelloZeroNet/ZeroNet) |
| ZeroNet Conservancy | Repositório principal atualizado em 22/02/2026; README descreve desenvolvimento como lento/esparso | [zeronet-conservancy/zeronet-conservancy](https://github.com/zeronet-conservancy/zeronet-conservancy) |
| ZeroMe do Conservancy | Repositório `0me` indicado como atualizado em 20/11/2022 | [zeronet-conservancy/0me](https://github.com/zeronet-conservancy/0me) |
| ZeroNetX | Repositório Python principal atualizado em 12/09/2025 | [ZeroNetX/ZeroNet](https://github.com/ZeroNetX/ZeroNet) |
| ZeroNetX Rust | Implementação Rust do protocolo; atualização observada em 27/04/2025 | [ZeroNetX/zeronet-rs](https://github.com/ZeroNetX/zeronet-rs) |
| Riza | Nova rede P2P em desenvolvimento; não tratar como fork compatível do ZeroNet | [Riza Committee](https://riza-committee.github.io/) |

**Conclusão de pesquisa:** entre os repositórios comparados, `zeronet-conservancy/zeronet-conservancy` apresentou a atualização pública mais recente. Isso não autoriza chamá-lo de “fork mais ativo” ou “mais saudável”: o próprio README alerta que o desenvolvimento é lento/esparso. ZeroNetX continua útil como referência de compatibilidade e como fonte do protótipo Rust, mas as datas observadas não sustentam chamá-lo de mais atualizado.

## 🌈 8. Referências técnicas para a implementação

- [OrbitDB — documentação/API](https://api.orbitdb.org/)
- [OrbitDB — Getting Started](https://github.com/orbitdb/orbitdb/blob/main/docs/GETTING_STARTED.md)
- [OrbitDB — repositório](https://github.com/orbitdb/orbitdb)
- [Helia — repositório e arquitetura modular](https://github.com/ipfs/helia)
- [Helia — exemplos de armazenamento](https://github.com/ipfs-examples/helia-examples)
- [IPFS — Persistence](https://docs.ipfs.tech/concepts/persistence/)
- [Ethereum — Blockchain Data Storage Strategies](https://ethereum.org/developers/docs/data-availability/blockchain-data-storage-strategies/)
- [Ethereum — Data Availability](https://ethereum.org/developers/docs/data-availability/)

### 🌈 Observações técnicas importantes

1. A documentação do OrbitDB descreve bancos P2P com armazenamento IPFS, sincronização por Libp2p PubSub e consistência eventual baseada em Merkle-CRDTs. Isso não significa que todos os bancos devam ser replicados por todos os peers nem que conflitos de produto estejam resolvidos automaticamente.
2. O guia de início do OrbitDB alerta que Helia usa armazenamento em memória por padrão no exemplo básico. Sem blockstore persistente, os blocos deixam de estar disponíveis após o encerramento da aplicação. Configurar armazenamento persistente é requisito de produção, não otimização futura.
3. IPFS depende de retenção/pinning para persistência prática. O CID identifica e verifica conteúdo, mas não obriga a rede a manter uma cópia disponível para sempre.
4. Ethereum distingue armazenamento persistente, eventos, calldata e dados externos. Cada opção tem custos e propriedades diferentes. Um hash on-chain prova integridade de uma referência, não disponibilidade permanente do conteúdo off-chain.
5. O suporte a hashers diferentes dos padrões de uma implementação deve ser verificado. Não presumir que escolher um algoritmo de CID garante compatibilidade automática em todos os clientes e gateways.

## 🌈 9. Registro de execução

Use este espaço para acompanhar o trabalho real. Não marque tarefas como concluídas apenas porque foram discutidas.

| Data | Item | Evidência/commit | Estado | Observações |
|---|---|---|---|---|
| 17/11/2026 | Documento inicial de arquitetura e riscos | Este arquivo | Planejamento | Nenhuma implementação declarada |

---

## 🌈 Regra final

**Não inventar implementação para preencher TODO.** Se uma decisão não foi testada, ela continua pendente. Se algo mudou, documentar a razão e o impacto. Se modificou, commitar; se entregou, preservar o `.git/`; se não terminou, atualizar o TODO.
