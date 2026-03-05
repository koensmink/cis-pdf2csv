# Threat Model (STRIDE)

Dit project gebruikt het **STRIDE threat model** om potentiële risico's
te analyseren.

| Type | Betekenis |
|------|-----------|
| S | Spoofing (identiteitsvervalsing) |
| T | Tampering (manipulatie van data) |
| R | Repudiation (ontkennen van acties) |
| I | Information Disclosure (informatie lekken) |
| D | Denial of Service |
| E | Elevation of Privilege |

# STRIDE Analyse

## Spoofing

### Dreiging

Een aanvaller kan proberen een gemanipuleerd CIS benchmark document aan
te bieden.

### Risico

zeer-Laag

------------------------------------------------------------------------

## Tampering

### Dreiging

Manipulatie van:

-   input benchmark bestanden
-   gegenereerde CSV/JSONL output
-   container image

### Risico

Laag

### Mitigatie

De parser registreert meerdere integriteitsvelden:

-   `source_pdf_sha256`
-   `block_text_sha256`
-   `parser_version`
-   `extracted_at_utc`

Hiermee kan altijd worden herleid:

PDF → control → CSV record

Daarnaast worden resultaten gesorteerd:

benchmark_name → benchmark_version → control_id

Dit maakt diffing en integriteitscontrole mogelijk.

------------------------------------------------------------------------

## Repudiation

### Dreiging

Een gebruiker ontkent dat een bestand door de parser is gegenereerd.

### Mitigatie

De output bevat metadata:

-   benchmark_name
-   benchmark_version
-   benchmark_date
-   source_pdf_sha256
-   parser_version
-   extracted_at_utc

Hiermee kan de herkomst van de data worden vastgesteld.

------------------------------------------------------------------------

## Information Disclosure

### Dreiging

Onbedoeld lekken van gevoelige informatie via logs of output.

### Risico

Laag

### Reden

De tool verwerkt uitsluitend **publieke CIS benchmark documenten**.

Er worden geen:

-   credentials
-   API keys
-   externe services

gebruikt.

De tool werkt volledig offline.

------------------------------------------------------------------------

## Denial of Service

### Dreiging

Malicious PDF bestanden kunnen proberen:

-   parser libraries te crashen
-   extreem geheugenverbruik te veroorzaken

### Risico

Medium

### Mitigatie

Container sandboxing wordt aanbevolen:

docker run --read-only --tmpfs /tmp --cap-drop ALL --security-opt
no-new-privileges

Hiermee wordt de impact van een eventuele parser kwetsbaarheid beperkt.

------------------------------------------------------------------------

## Elevation of Privilege

### Dreiging

Een exploit in de PDF parser kan proberen privileges te verhogen.

### Risico

Laag

### Mitigatie

De container draait:

-   als **non-root user**
-   zonder Linux capabilities
-   met **no-new-privileges**
-   met read-only filesystem

Voorbeeld veilige runtime:

docker run --read-only --tmpfs /tmp --cap-drop ALL --security-opt
no-new-privileges cis-pdf2csv

------------------------------------------------------------------------

# Dependency Security

Belangrijkste dependencies:

-   Python 3.11
-   PyMuPDF
-   Pydantic
-   Rich

Container base image:

python:3.11-slim

Security maatregelen:

-   pip / wheel / setuptools upgrade tijdens build
-   container draait non-root
-   minimale runtime dependencies

------------------------------------------------------------------------

# Security Best Practices

Aanbevolen runtime configuratie:

docker run --read-only --tmpfs /tmp --cap-drop ALL --security-opt
no-new-privileges cis-pdf2csv

Aanvullende aanbevelingen:

-   verwerk alleen vertrouwde benchmark bestanden
-   update container images regelmatig
-   scan images periodiek op kwetsbaarheden
