TasMesh: keep known nodes reachable when MeshBroker is run again

## Description:

`MESHstartBroker()` calls `esp_now_deinit()` then `esp_now_init()`, which empties the ESP-NOW peer table. The list of known nodes in `MESH.peers` is kept. When a node then registers again, `MESHcheckPeerList()` finds it in `MESH.peers` and `MESHaddPeer()` is not called, so the node is never added back to ESP-NOW. The broker sends with `esp_now_send(NULL, ...)`, i.e. to every peer of the (now empty) table: from then on nothing reaches any node, and nothing is logged.

Running `MeshBroker` a second time is easy to do: from the console, or from a rule such as `on wifi#connected do meshbroker endon` after a reconnection, which may also change the Wi-Fi channel.

The fix adds the nodes already in `MESH.peers` back to the ESP-NOW peer table right after `esp_now_init()`, on the current channel. Nodes keep their topic and the broker keeps its MQTT subscriptions, so they do not have to register again.

Depends on #25342: without it, no command reaches a node, so the problem cannot be seen.

**How it was checked, on hardware** (same setup as #25342: ESP32 broker, core 3.3.12, IDF 5.5.5; ESP8266 Wemos D1 mini node, core 2.7.8):
- before: after a second `MeshBroker`, commands for the node are intercepted (`MSH: Intercept payload ...`) but never sent (no `MSH: Sent to ...`), and the node runs nothing; only a restart of the broker recovers;
- after: `MeshBroker`, `MeshNode` on the node, `Power` (reaches the node), then `MeshBroker` again: the next `Power` and `Power 1` are still sent (`MSH: Sent to EC:FA:BC:CB:30:05 status 0`) and run by the node (`POWER1 = ON`), without the node registering again; `Status 10` still shows `"nodes":1`.

**Related issue (if applicable):** none

## Checklist:
  - [x] The pull request is done against the latest development branch
  - [x] Only relevant files were touched
  - [x] Only one feature/fix was added per PR and the code change compiles without warnings
  - [x] The code change is tested and works with Tasmota core ESP8266 V.2.7.8
  - [x] The code change is tested and works with Tasmota core ESP32 V.3.3.12-3 from Platform 2026.11.51
  - [x] I accept the [CLA](https://github.com/arendst/Tasmota/blob/development/CONTRIBUTING.md#contributor-license-agreement-cla).

_NOTE: The code change must pass CI tests. **Your PR cannot be merged unless tests pass**_
