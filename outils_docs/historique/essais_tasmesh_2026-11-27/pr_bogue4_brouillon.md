TasMesh: keep known nodes reachable when MeshBroker is run again

## Description:

`MESHstartBroker()` calls `esp_now_deinit()` then `esp_now_init()`, which empties the ESP-NOW peer table. The list of known nodes in `MESH.peers` is kept. When such a node registers again, `MESHcheckPeerList()` finds it in `MESH.peers`, so `MESHaddPeer()` is not called and the node is never added back to ESP-NOW. The broker sends with `esp_now_send(NULL, ...)`, i.e. to the peers of that table: from then on nothing reaches the already known nodes, and nothing is logged.

`MeshBroker` can easily run a second time: from the console, or from a rule that fires again, for instance after a Wi-Fi reconnection.

The fix adds the nodes in `MESH.peers` back to the ESP-NOW peer table right after `esp_now_init()`. Their topics and the MQTT subscriptions are kept, so on an unchanged channel they do not have to register again. If the Wi-Fi channel has changed, a node still has to run `MeshNode` again to move to it (not tested).

Follow-up to #25342: before it, no command reached a node, so this could not be seen.

**How it was checked, on hardware** (ESP32 broker, core 3.3.12, Platform 2026.11.51; ESP8266 Wemos D1 mini node, core 2.7.8):
- before: after a second `MeshBroker`, the broker still intercepts commands for the node (`MSH: Intercept payload ...`) but logs no `MSH: Sent to ...`, and the node runs nothing, even after `MeshNode` is run again on the node. It works again after restarting the boards;
- after: `MeshBroker`, `MeshNode` on the node, then `MeshBroker` again, with no new `MeshNode`: commands are still sent (`MSH: Sent to <node MAC> status 0`) and run by the node (`POWER1 = ON`), and `Status 10` still shows `"nodes":1`. This was done twice, with the same result.

About two minutes after the first of these two runs, the broker restarted once by itself (`Software reset CPU`). The crash record was not usable (reason `Unknown`, and the addresses only decoded to the idle task), so I do not know the cause. In the second run the broker was watched for about 4 minutes after the second `MeshBroker`: it kept reaching the node and did not restart.

**Related issue (if applicable):** none

## Checklist:
  - [x] The pull request is done against the latest development branch
  - [x] Only relevant files were touched
  - [x] Only one feature/fix was added per PR and the code change compiles without warnings
  - [x] The code change is tested and works with Tasmota core ESP8266 V.2.7.8
  - [x] The code change is tested and works with Tasmota core ESP32 V.3.3.12-3 from Platform 2026.11.51
  - [x] I accept the [CLA](https://github.com/arendst/Tasmota/blob/development/CONTRIBUTING.md#contributor-license-agreement-cla).

_NOTE: The code change must pass CI tests. **Your PR cannot be merged unless tests pass**_

🤖 Generated with [Claude Code](https://claude.com/claude-code)
