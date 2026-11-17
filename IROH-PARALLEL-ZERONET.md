# Iroh em paralelo à ZeroNet

**Status:** estudo arquitetural, não implementação  
**Escopo:** adicionar transporte Iroh sem quebrar clientes, sites ou conteúdo ZeroNet existentes  
**Repositório analisado:** `FloflisPull/ZirohNeth`  
**Base analisada:** `main` em `dfb0e9ed390006cde9365354572120c62fcf6119`

## 1. Resumo executivo

A recomendação é introduzir Iroh como **um transporte adicional e opcional**, não como substituto imediato do protocolo ZeroNet.

A ZeroNet atual tem responsabilidades que não podem ser confundidas:

1. identidade e autorização de conteúdo;
2. descoberta e seleção de peers;
3. transporte de mensagens e streams;
4. armazenamento, verificação e atualização dos arquivos.

Iroh pode ajudar principalmente nos itens 2 e 3, e `iroh-blobs` pode oferecer um caminho alternativo para transporte/armazenamento de blobs. Isso não autoriza remover a validação ZeroNet de `content.json`, as assinaturas, os hashes legados ou a política de acesso.

**Princípio de compatibilidade:** um arquivo recebido por TCP/ZeroNet ou por Iroh deve passar exatamente pela mesma validação já aplicada pelo cliente.

## 2. O que foi confirmado no código

### 2.1 Transporte ZeroNet

Arquivos examinados:

- `src/Connection/Connection.py`
- `src/Connection/ConnectionServer.py`
- `src/Peer/Peer.py`
- `src/File/FileServer.py`

Observações verificadas:

- `ConnectionServer` aceita conexões com `gevent.server.StreamServer`.
- `Connection` implementa handshake próprio e troca mensagens MessagePack.
- O handshake informa versão/protocolo, `peer_id`, porta do fileserver, endereços e capacidades de criptografia.
- A conexão pode negociar TLS (`tls-rsa`) por meio de `CryptConnection`.
- `Connection.messageLoop()` lê do socket, alimenta o unpacker MessagePack e despacha mensagens.
- O caminho de stream envia cabeçalho/mensagem e depois bytes brutos pelo mesmo socket.
- `Peer.request()` abre/reabre conexões e executa comandos ZeroNet.
- `Peer.getFile()` usa `getFile` ou `streamFile`, com leituras em partes.
- `Peer.pex()` troca endereços de peers e filtra tipos de endereço não suportados.

Esses elementos formam um protocolo de aplicação próprio. QUIC/Iroh não é uma troca transparente de socket TCP: framing, handshake, multiplexação, identidade de endpoint e ciclo de vida precisam ser adaptados.

### 2.2 Descoberta de peers

Arquivos examinados:

- `src/Site/SiteAnnouncer.py`
- `plugins/AnnounceBitTorrent/AnnounceBitTorrentPlugin.py`
- `src/DHT/DHTServer.py`
- `src/Peer/Peer.py`

Observações verificadas:

- `SiteAnnouncer` executa anúncios para trackers e também chama `announceDHT()`.
- O DHT atual usa `aiobtdht`/`aioudp` e nós bootstrap BitTorrent.
- O plugin `AnnounceBitTorrent` implementa handlers de trackers UDP/HTTP/HTTPS.
- `Peer.pex()` fornece peer exchange sobre uma conexão ZeroNet já estabelecida.

Portanto, a descoberta atual não é somente BitTorrent tracker: há DHT e PEX. A descoberta Iroh deve coexistir com essas fontes, não apagá-las.

### 2.3 Integridade e identidade de conteúdo

Arquivos examinados:

- `src/Content/ContentManager.py`
- `src/Site/SiteStorage.py`
- `src/Crypt/CryptHash.py`
- `src/Crypt/CryptBitcoin.py`

O cliente carrega e valida `content.json`, usa assinaturas associadas à identidade do site e verifica arquivos segundo os hashes descritos no conteúdo. `CryptHash.sha512sum()` implementa SHA-512 truncado a 256 bits para a função usada pelo projeto.

**Não substituir os hashes ou assinaturas existentes por BLAKE3/CID como parte da primeira integração Iroh.** Um identificador de blob Iroh deve ser metadado de transporte/lookup, associado ao caminho e ao hash ZeroNet esperado. A verificação final continua sendo a ZeroNet.

## 3. Modelo de integração proposto

### Fase A: transporte paralelo, sem mudar descoberta

Adicionar um adaptador interno com interface conceitual semelhante a:

```text
Transport
  connect(peer_descriptor)
  request(command, params)
  receive_stream(stream_descriptor, sink)
  close()
  capabilities()
```

Implementações iniciais:

- `ZeroNetTcpTransport`: encapsula o comportamento atual, sem alterar protocolo.
- `IrohTransport`: implementação nova, inicialmente experimental.

A interface é uma proposta, não uma descrição de código existente.

O primeiro protótipo deve transferir um arquivo de teste entre dois nós Iroh e entregar os bytes ao pipeline de validação atual. Não deve anunciar sites publicamente nem alterar a seleção normal de peers.

### Fase B: identidade e descoberta Iroh

Avaliar como representar um endpoint Iroh no registro local de peers. Não assumir que `peer_id`, endereço IP/porta ou identidade de site ZeroNet equivalem a um `EndpointId` Iroh.

O descritor deve manter campos separados:

- identidade ZeroNet/site;
- identidade de endpoint Iroh;
- capacidades e versão do transporte;
- endereço/relay, quando aplicável;
- validade/expiração e origem da descoberta.

Fontes de descoberta podem incluir bootstrap/discovery Iroh, anúncios ZeroNet existentes e PEX. A procedência do endereço deve ser registrada; um endpoint descoberto não é automaticamente confiável.

### Fase C: blobs

Avaliar `iroh-blobs` para transporte e disponibilidade de conteúdo endereçado por hash. Criar uma associação explícita:

```text
(site_address, inner_path, zeronet_hash, expected_size)
    -> (iroh_blob_hash, blob_format_version)
```

A associação deve ser descartável e reconstruível. O hash ZeroNet continua sendo a autoridade de integridade para o arquivo ZeroNet.

Não presumir que o CID de um blob é compatível com o hash ZeroNet. Não confundir BLAKE3, SHA-512 truncado, CIDv1, `EndpointId` e identidade de site.

## 4. Limites e compatibilidade

### Clientes antigos

- Clientes sem Iroh continuam usando TCP, trackers, DHT e PEX atuais.
- Um peer Iroh-only não deve ser anunciado como se fosse um peer TCP convencional.
- Não alterar o handshake ZeroNet existente para exigir Iroh.
- Se houver anúncio de capacidades, ele precisa ser aditivo e ignorável por clientes antigos.

### Tor e proxies

O projeto possui caminhos especiais para `.onion`, SOCKS e configurações de proxy. O transporte Iroh precisa ser testado separadamente nesses cenários. Não presumir que relays Iroh respeitam automaticamente a política Tor/proxy configurada pelo usuário.

A primeira versão deve manter Iroh desativado quando não for possível garantir a política de rede selecionada. Documentar explicitamente o que é roteado pelo Tor, o que pode usar relay e o que pode revelar endereço IP.

### Segurança

- Validar tamanho máximo, limites de memória e backpressure.
- Tratar dados remotos como não confiáveis.
- Vincular o blob ao site/caminho/hash esperado antes de persistir.
- Evitar que descoberta de endpoint conceda autorização.
- Não aceitar conteúdo só porque o transporte autenticou um endpoint.
- Testar replay, truncamento, conteúdo malformado, peer malicioso e indisponibilidade de relay.
- Preservar a validação de assinatura e de hash do pipeline atual.

## 5. Plano de experimentos

1. **PoC isolada:** dois processos Rust Iroh trocam um blob pequeno e um arquivo maior.
2. **Adaptador local:** Python chama um processo/serviço Rust local, sem mexer no `Peer` existente.
3. **Validação ZeroNet:** bytes recebidos são enviados ao mesmo verificador usado pelo download TCP.
4. **Fallback:** desligar Iroh durante uma transferência e comprovar que o download TCP continua possível.
5. **Interoperabilidade:** cliente antigo continua operando sem conhecer Iroh.
6. **Rede difícil:** NAT, IPv4/IPv6, relay indisponível, Tor/proxy e reconexão.
7. **Carga:** memória, CPU, throughput, latência, número de conexões e custo de relay.

Cada experimento deve ter logs que identifiquem o transporte, peer, site, caminho, bytes, duração e resultado da validação, sem registrar segredos.

## 6. Critérios de decisão

Iroh só deve sair do modo experimental quando:

- a transferência funcionar em redes suportadas com fallback previsível;
- o conteúdo passar pela validação ZeroNet sem exceções;
- clientes antigos permanecerem compatíveis;
- a política de privacidade/rede estiver documentada;
- testes automatizados cobrirem falhas e peers maliciosos;
- a dependência Rust e sua versão estiverem fixadas e reproduzíveis nos builds.

## 7. Riscos e questões em aberto

- Qual versão de `iroh` e `iroh-blobs` será adotada? A API e o ciclo de versões dos crates precisam ser conferidos no momento da implementação; não fixar versões com base neste estudo.
- O processo Iroh será biblioteca embutida via PyO3 ou daemon local com IPC? O daemon reduz acoplamento inicial e facilita crash isolation; PyO3 reduz overhead de IPC, mas aumenta complexidade de build/ABI.
- Como associar identidade de site e identidade de endpoint sem criar uma autoridade paralela?
- Quais modos Iroh funcionam sob Tor e proxies suportados pelo cliente?
- Como persistir o índice blob sem torná-lo fonte autoritativa?
- Como limitar armazenamento, pinning e garbage collection?

## 8. Referências técnicas

- Iroh: https://github.com/n0-computer/iroh
- Documentação Iroh: https://docs.rs/iroh/
- Iroh blobs: https://github.com/n0-computer/iroh
- Documentação iroh-blobs: https://docs.rs/iroh-blobs/
- Iroh docs: https://docs.rs/iroh-docs/
- ZeroNet connection: `src/Connection/Connection.py`
- ZeroNet peer: `src/Peer/Peer.py`
- ZeroNet discovery: `src/Site/SiteAnnouncer.py`, `src/DHT/DHTServer.py`
- ZeroNet content verification: `src/Content/ContentManager.py`, `src/Site/SiteStorage.py`

## 9. TODO

- [ ] Confirmar versões estáveis e matrizes de compatibilidade dos crates no início da implementação.
- [ ] Criar PoC Rust independente para Iroh endpoint + blob.
- [ ] Definir IPC/daemon versus PyO3.
- [ ] Definir esquema de associação ZeroNet hash ↔ Iroh blob hash.
- [ ] Testar Tor/proxy e documentar vazamentos de metadados.
- [ ] Adicionar testes de fallback TCP e validação de conteúdo.
- [ ] Não alterar protocolo legado antes de resultados dos experimentos.
