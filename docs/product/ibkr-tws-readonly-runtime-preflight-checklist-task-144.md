# Task 144 — IBKR TWS/Gateway read-only runtime preflight checklist

## 1. Purpose
Deze checklist is een **harde preflight-gate** vóór enige toekomstige implementatie van echte TWS/Gateway read-only runtime connectiviteit. Deze taak is documentatie/preflight-only en activeert geen runtime connectiviteit.

## 2. Current state after Task 143
- Session-status diagnostics bestaan al met expliciete adapterselectie en blocked reason-codes.
- Standaardpad blijft veilige non-network adapter.
- Runtimeconnectiviteit naar echte TWS/Gateway is nog niet geïmplementeerd of geactiveerd.

## 3. What is already built
- Disabled-by-default adapter boundary en selectiepad.
- Session-status endpointdiagnostiek met veilige status/reason mapping.
- Readiness/safety discipline: orders/suggesties/action drafts blijven geblokkeerd.

## 4. What is still not built
- Geen echte low-level IBKR runtime client.
- Geen socketverbinding naar TWS/Gateway.
- Geen runtime account/portfolio sync, market-data runtime of FX runtime.
- Geen auto-connect, reconnect loop of persistente session manager.

## 5. Hard safety boundaries
- Version 1 blijft paper-only.
- Geen live trading, real-money execution, broker execution of automatische orders.
- AI blijft uitleg/research; geen execution.
- Deze preflight staat alleen read-only status-check runtime voorbereiding toe, geen orderflow.

## 6. Required configuration gates
Verplicht vóór runtime wiring:
- `ibkr_enabled=True` **mag nooit** op zichzelf verbinden.
- `ibkr_status_check_enabled=True` **mag nooit** op zichzelf verbinden.
- `ibkr_tws_readonly_adapter_enabled=True` **mag nooit** op zichzelf verbinden.
- Een toekomstige dedicated runtime-toggle is verplicht en staat standaard op `False`.
- TWS/Gateway runtime blijft disabled-by-default.
- Paper-only enforcement blijft verplicht.

## 7. Required environment/config rules
- Toegestane configuratie voor toekomstige runtime-taak:
  - alleen expliciete opt-in toggles;
  - alleen paper account context;
  - alleen handmatige status-check lifecycle.
- Verboden defaults:
  - auto-connect bij API startup;
  - impliciete connectie op basis van één losse flag;
  - runtime-enable zonder complete preflight-pass.

## 8. Required account-mode checks
- Alleen `paper` account mode mag runtime-attempt toestaan.
- `live`/real-money mode moet hard blokkeren.
- `unknown` account mode moet hard blokkeren.
- Mismatch tussen verwachte en gedetecteerde account mode moet hard blokkeren.
- Blokkades moeten zichtbaar zijn via eenvoudige Nederlandse diagnostiek.
- Account-mode pass alleen mag nooit sync/suggestie/action/order activeren.

## 9. Required read-only connection lifecycle rules
- Geen auto-connect op startup.
- Geen reconnect loop.
- Geen persistente worker-managed session manager in de eerste runtime-slice.
- Eerste runtime-slice mag alleen handmatige/status-check lifecycle bevatten.
- Iedere connectiepoging moet timeout handling hebben.
- Disconnect moet veilig geprobeerd worden.
- Disconnect-fouten mogen API-proces niet laten crashen.
- Runtime errors moeten mappen naar bestaande veilige statuscodes of vooraf gedocumenteerde nieuwe codes.

## 10. Required no-secret/no-raw-config exposure rules
Nooit exposen via API/UI/logs:
- ruwe host/port/client ID;
- account credentials, tokens, wachtwoorden of secrets;
- ruwe broker payloads.
Alleen veilige geabstraheerde velden tonen, bijvoorbeeld `configured: true/false`.

## 11. Required tests before any real runtime task
Verplicht vóór merge van een runtime-taak:
- Default settings maken geen connectiepoging.
- Expliciete combinatie van settings is vereist vóór connectiepoging.
- Geïnjecteerde fake low-level client dekt lifecycle contracten.
- Timeout -> veilige status mapping.
- Authentication required -> veilige status mapping.
- Pacing limited -> veilige status mapping.
- Wrong account mode -> veilige status mapping.
- Unknown account mode -> veilige status mapping.
- Disconnect wordt veilig aangeroepen.
- Secrets blijven afgeschermd.
- Geen order/suggestie/action booleans worden `true`.
- CI groen op alle zes jobs: `domain`, `storage`, `portfolio`, `api`, `worker`, `web`.

## 12. Required manual/operator checks
Vóór eerste runtime-attempt in latere taak:
- Operator bevestigt expliciet paper-account context.
- Operator bevestigt dat runtime-toggle bewust is geactiveerd.
- Operator bevestigt handmatige status-check use-case (geen continue sessiebeheer).
- Operator bevestigt rollback-pad en disable-switch beschikbaar.

## 13. Required failure handling
Elke foutstatus vereist machine-code, eenvoudige NL-tekst, veilige next-step, en geen order/suggestie/action enablement:
- `connection_failed`
- `timeout`
- `authentication_required`
- `pacing_limited`
- `wrong_account_mode`
- `unknown_account_mode`
- `missing_runtime_client`
- `runtime_disabled`
- `configuration_missing`
- `unsafe_account_mode`
- `unexpected_client_error`

## 14. Required rollback/disable behavior
- Eén expliciete runtime disable-switch moet toekomstige runtime direct kunnen stoppen.
- Na disable moet status veilig terugvallen naar non-connected/blocked zonder crash.
- Rollback-procedure moet runtime toggles terugzetten naar disabled defaults.

## 15. Explicitly forbidden scope
Nog steeds verboden in Version 1:
- real runtime broker execution;
- order submission/modify/cancel;
- live/real-money execution;
- automatic orders;
- options, futures, leverage, short selling, crypto, penny stocks, CFD, complex derivatives;
- fake broker/portfolio/market runtime data;
- storage schema/migraties voor deze preflighttaak.

## 16. Recommended next implementation task
**Task 145 — Add dependency-free manual TWS/Gateway read-only status-check runtime client boundary with injected fake client tests only.**

## 17. Acceptance criteria for the next implementation task
Task 145 is alleen acceptabel als:
- alle checklistgates hierboven aantoonbaar zijn geïmplementeerd;
- runtime standaard disabled blijft;
- alleen manual/status-check lifecycle bestaat;
- alleen paper-mode connectiepogingen zijn toegestaan;
- geen third-party IBKR dependency wordt toegevoegd tenzij expliciet later vrijgegeven;
- geen runtime scope buiten read-only status-check wordt toegevoegd.
