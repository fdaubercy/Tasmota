/*
   user_config_override.h - Remplace la configuration utilisateur my_user_config.h pour Tasmota
   Copyright (C) 2021 Theo Arends

   Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le modifier
   selon les termes de la Licence Publique Générale GNU (GPL) telle que publiée par
   la Free Software Foundation, soit la version 3 de la Licence, soit
   (à votre choix) toute version ultérieure.

   Ce programme est distribué dans l'espoir qu'il sera utile,
   mais SANS AUCUNE GARANTIE ; sans même la garantie implicite de
   QUALITÉ MARCHANDE ou d'ADÉQUATION À UN USAGE PARTICULIER. Consultez la
   Licence Publique Générale GNU pour plus de détails.

   Vous auriez dû recevoir une copie de la Licence Publique Générale GNU
   avec ce programme. Sinon, consultez <http://www.gnu.org/licenses/>.
*/

/*
Pour tout nouveau ESP32-P4, mettre à jour l'ESP32-C6 vers la derniere version de son firmware
    Commande pour mettre à jour l'ESP32-C6 de l'ESP32-P4 Wifi6: HostedOTA https://ota.tasmota.com/tasmota32/coprocessor/network_adapter_esp32c6.bin
    Update du fichier de l'HostedMCU: HostedLoad https://ota.tasmota.com/tasmota32/coprocessor/network_adapter_esp32c6.bin
    Fichier du firmware de l'ESP32-C6 Hosted, enregistré dans 'build_output/firmware/network_adapter_esp32c6.bin'
*/

#ifndef _USER_CONFIG_OVERRIDE_H_
    #define _USER_CONFIG_OVERRIDE_H_

    /*****************************************************************************************************\
    * USAGE:
    * Pour modifier la configuration par défaut sans modifier le fichier my_user_config.h :
    * (1) Copiez ce fichier et renommez-le « user_config_override.h » (il sera ignoré par Git).
    * (2) Définissez vos propres paramètres ci-dessous.
    *
    ******************************************************************************************************
    * ATTENTION:
    * - Les modifications apportées aux définitions de PARAMETER de la SECTION 1 ne remplaceront les paramètres flash que si vous modifiez la définition CFG_HOLDER.
    * - Des avertissements du compilateur s'afficheront si aucune séquence ifdef/undef/endif n'est utilisée.
    * - Vous devez toujours mettre à jour my_user_config.h pour la définition majeure USE_MQTT_TLS.
    * - Tous les paramètres peuvent être modifiés en ligne de manière permanente à l'aide de commandes via MQTT, la console Web ou le port série.
    \*****************************************************************************************************/

    /*********************************************************************************************\
     * SECTION 1
     * - Après le chargement initial, toute modification apportée ici ne sera prise en compte 
     * que si CFG_HOLDER est également modifié.
    \*********************************************************************************************/
    //  #warning *** ------------------- Le fichier 'user_config_override.ini' est appele ------------------- ***
    #if defined(CFG_HOLDER) && (CFG_HOLDER == 4617)
        #undef CFG_HOLDER
		#define CFG_HOLDER 		1326			// [Reset 1] Change this value to load SECTION1 configuration parameters to flash

        // #pragma message(*** ------------------- Les paramètres flash seront remplacés ! ------------------- ***)
    #else
        // #pragma message(*** ------------------- Les paramètres flash ne seront pas remplacés ! ------------------- ***)
    #endif

    // Controle les sections à activer
    #define USER_CONFIG_OVERRIDE_SECTION1                           // Section 1 - Paramètres de configuration de base
    #define USER_CONFIG_OVERRIDE_SECTION2                           // Section 2 - Activer/désactiver les fonctionnalités
    #define USER_CONFIG_OVERRIDE_FIRMWARES_PERSONNALISES            // Section 3 - Firmwares personnalisés 
    #define USER_CONFIG_OVERRIDE_DEBUG                              // Fonctionnalités de débogage
    #define USER_CONFIG_OVERRIDE_PROFILING                          // Fonctionnalités de profilage
    #define USER_CONFIG_OVERRIDE_SAFE_GUARD                         // Fonctionnalités de Safe Guard
    #define USER_CONFIG_OVERRIDE_POST_PROCESS                       // Fonctionnalités de Post-traitement 
    #define USER_CONFIG_OVERRIDE_MUTUAL_EXCLUDE                     // Options d'exclusion mutuelle
    #define USER_CONFIG_OVERRIDE_POST_PROCESS_COMPILE_OPTIONS       // Options de compilation Post-traitement 

    #ifdef USER_CONFIG_OVERRIDE_SECTION1
        // -- Wi-Fi ---------------------------------------
        #ifdef WIFI_IP_ADDRESS
            #undef WIFI_IP_ADDRESS
        #endif
        #define WIFI_IP_ADDRESS        "0.0.0.0"           // [IpAddress1] Set to 0.0.0.0 for using DHCP or enter a static IP address  
        #ifdef WIFI_GATEWAY
            #undef WIFI_GATEWAY
        #endif
        #define WIFI_GATEWAY           "192.168.0.254"     // [IpAddress2] If not using DHCP set Gateway IP address
        #ifdef WIFI_SUBNETMASK
            #undef WIFI_SUBNETMASK
        #endif
        #define WIFI_SUBNETMASK        "255.255.255.0"     // [IpAddress3] If not using DHCP set Network mask
        #ifdef WIFI_DNS
            #undef WIFI_DNS
        #endif
        #define WIFI_DNS               "192.168.0.254"     // [IpAddress4] If not using DHCP set DNS1 IP address (might be equal to WIFI_GATEWAY)
        #ifdef WIFI_DNS2
            #undef WIFI_DNS2
        #endif
        #define WIFI_DNS2              "192.168.0.254"     // [IpAddress5] If not using DHCP set DNS2 IP address (might be equal to WIFI_GATEWAY)

        #ifdef STA_SSID1
            #undef STA_SSID1
        #endif
        #define STA_SSID1              "MAISON"                                    // [Ssid1] Wi-Fi SSID
        #ifdef STA_PASS1
            #undef STA_PASS1
        #endif
        #define STA_PASS1              "obdormisti-pervigile%.-ficiendus"          // [Password1] Wi-Fi password
        #ifdef STA_SSID2
            #undef STA_SSID2
        #endif
        #define STA_SSID2              "Relai Wifi 2.4G KuWFi"                     // [Ssid2] Optional alternate AP Wi-Fi SSID
        #ifdef STA_PASS2
            #undef STA_PASS2
        #endif
        #define STA_PASS2              "obdormisti-pervigile%.-ficiendus"          // [Password2] Optional alternate AP Wi-Fi password

        #ifdef WIFI_AP_PASSPHRASE
            #undef WIFI_AP_PASSPHRASE
        #endif
        #define WIFI_AP_PASSPHRASE     ""                                          // AccessPoint passphrase. For WPA2 min 8 char, for open use "" (max 63 char).
        #ifdef WIFI_CONFIG_TOOL
            #undef WIFI_CONFIG_TOOL
        #endif
        #define WIFI_CONFIG_TOOL       WIFI_MANAGER                                // [WifiConfig] Default tool if Wi-Fi fails to connect (default option: 4 - WIFI_RETRY)
                                                                                    //  (WIFI_RESTART, WIFI_MANAGER, WIFI_RETRY, WIFI_WAIT, WIFI_SERIAL, WIFI_MANAGER_RESET_ONLY)
                                                                                    //  The configuration can be changed after first setup using WifiConfig 0, 2, 4, 5, 6 and 7.

        // -- Wi-Fi Scan ---------------------------------- 
        #ifdef DNS_TIMEOUT
            #undef DNS_TIMEOUT
        #endif 
        #define DNS_TIMEOUT            1000              // [DnsTimeout] Number of ms before DNS timeout
        #ifdef WIFI_ARP_INTERVAL
            #undef WIFI_ARP_INTERVAL
        #endif
        #define WIFI_ARP_INTERVAL      60                // [SetOption41] Send gratuitous ARP interval 
        #ifdef WIFI_SCAN_REGULARLY
            #undef WIFI_SCAN_REGULARLY
        #endif 
        #define WIFI_SCAN_REGULARLY    true              // [SetOption57] Scan Wi-Fi network every 44 minutes for configured AP's
        #ifdef WIFI_NO_SLEEP
            #undef WIFI_NO_SLEEP
        #endif 
        #define WIFI_NO_SLEEP          false             // [SetOption127] Sets Wifi in no-sleep mode which improves responsiveness on some routers

        // -- Syslog --------------------------------------
        #ifdef SYS_LOG_HOST
            #undef SYS_LOG_HOST
        #endif
        #define SYS_LOG_HOST           "192.168.0.2"                // [LogHost] (Linux) syslog host
        #ifdef SYS_LOG_PORT
            #undef SYS_LOG_PORT
        #endif
        #define SYS_LOG_PORT           514                          // [LogPort] default syslog UDP port
        #ifdef SYS_LOG_LEVEL
            #undef SYS_LOG_LEVEL
        #endif
        #define SYS_LOG_LEVEL          LOG_LEVEL_DEBUG              // [SysLog] (LOG_LEVEL_NONE, LOG_LEVEL_ERROR, LOG_LEVEL_INFO, LOG_LEVEL_DEBUG, LOG_LEVEL_DEBUG_MORE)
        #ifdef SERIAL_LOG_LEVEL
            #undef SERIAL_LOG_LEVEL
        #endif
        #define SERIAL_LOG_LEVEL       LOG_LEVEL_DEBUG              // [SerialLog] (LOG_LEVEL_NONE, LOG_LEVEL_ERROR, LOG_LEVEL_INFO, LOG_LEVEL_DEBUG, LOG_LEVEL_DEBUG_MORE)
        #ifdef WEB_LOG_LEVEL
            #undef WEB_LOG_LEVEL
        #endif
        #define WEB_LOG_LEVEL          LOG_LEVEL_DEBUG              // [WebLog] (LOG_LEVEL_NONE, LOG_LEVEL_ERROR, LOG_LEVEL_INFO, LOG_LEVEL_DEBUG, LOG_LEVEL_DEBUG_MORE)
        #ifdef MQTT_LOG_LEVEL
            #undef MQTT_LOG_LEVEL
        #endif
        #define MQTT_LOG_LEVEL         LOG_LEVEL_DEBUG               // [MqttLog] (LOG_LEVEL_NONE, LOG_LEVEL_ERROR, LOG_LEVEL_INFO, LOG_LEVEL_DEBUG, LOG_LEVEL_DEBUG_MORE)

        // -- HTTP ----------------------------------------
        #define USE_CORS                                               // [Cors] Enable CORS - Be aware that this feature is unsecure ATM (https://github.com/arendst/Tasmota/issues/6767)
        #ifdef USE_CORS
            #ifdef CORS_DOMAIN
                #undef CORS_DOMAIN
            #endif
            #define CORS_DOMAIN                       ""                // [Cors] CORS Domain for preflight requests
        #endif

        // -- HTTP Options --------------------------------
        #ifdef GUI_NOSHOW_MODULE
            #undef GUI_NOSHOW_MODULE
        #endif
        #define GUI_NOSHOW_MODULE      true               // [SetOption141] Do not show module name in GUI main menu
        // #define GUI_NOSHOW_DEVICENAME  false              // [SetOption163] Do not show device name in GUI main menu
        // #define GUI_SHOW_HOSTNAME      false              // [SetOption53] Show hostname and IP address in GUI main menu
        // #define GUI_NOSHOW_STATETEXT   false              // [SetOption161] Do not show power state text in GUI

        // -- Setup your own MQTT settings  ---------------
        #ifdef MQTT_HOST
            #undef MQTT_HOST
        #endif
        #define MQTT_HOST         "192.168.0.5"          // [MqttHost]
        #ifdef MQTT_PORT
            #undef MQTT_PORT
        #endif
        #define MQTT_PORT         1883                   // [MqttPort] MQTT port (10123 on CloudMQTT)
        #ifdef MQTT_USER
            #undef MQTT_USER
        #endif
        #define MQTT_USER         "fdaubercy"       	 // [MqttUser] MQTT user
        #ifdef MQTT_PASS
            #undef MQTT_PASS
        #endif
        #define MQTT_PASS         "Lune5676"       		 // [MqttPassword] MQTT password

        // -- MQTT - Telemetry ----------------------------
        #ifdef TELE_PERIOD
            #undef TELE_PERIOD
        #endif
        #define TELE_PERIOD                       300               // [TelePeriod] Telemetry (0 = disable, 10 - 3600 seconds)
        #ifdef TELE_ON_POWER
            #undef TELE_ON_POWER
        #endif
        #define TELE_ON_POWER                     false             // [SetOption59] send tele/STATE together with stat/RESULT (false = Disable, true = Enable)

        // -- MQTT - Home Assistant Discovery -------------
        #ifdef HOME_ASSISTANT_DISCOVERY_ENABLE
            #undef HOME_ASSISTANT_DISCOVERY_ENABLE
        #endif
        #define HOME_ASSISTANT_DISCOVERY_ENABLE   true              // [SetOption19] Home Assistant Discovery (false = Disable, true = Enable)
        #ifdef HASS_AS_LIGHT
            #undef HASS_AS_LIGHT
        #endif
        #define HASS_AS_LIGHT                     false             // [SetOption30] Enforce HAss autodiscovery as light
        #define DEEPSLEEP_LWT_HA_DISCOVERY                        // Enable LWT topic and its payloads for read-only sensors (Status sensor not included) and binary_sensors on HAss Discovery (Commented out: all read-only sensors and binary_sensors
                                                                    // won't be shown as OFFLINE on Home Assistant when the device is DeepSleeping - NOTE: This is only for read-only sensors and binary_sensors, relays will be shown as OFFLINE)

        // -- MQTT - Options ------------------------------
        // #define MQTT_RESULT_COMMAND               false             // [SetOption4]  Switch between MQTT RESULT or COMMAND
        // #define MQTT_LWT_MESSAGE                  false             // [SetOption10] Switch between MQTT LWT OFFLINE or empty message
        #ifdef MQTT_POWER_FORMAT
            #undef MQTT_POWER_FORMAT
        #endif
        #define MQTT_POWER_FORMAT                 true              // [SetOption26] Switch between POWER or POWER1 for single power devices
        // #define MQTT_APPEND_TIMEZONE              false             // [SetOption52] Append timezone to JSON time
        // #define MQTT_BUTTON_SWITCH_FORCE_LOCAL    false             // [SetOption61] Force local operation when button/switch topic is set (false = off, true = on)
        // #define MQTT_INDEX_SEPARATOR              false             // [SetOption64] Enable "_" instead of "-" as sensor index separator
        // #define MQTT_TUYA_RECEIVED                false             // [SetOption66] Enable TuyaMcuReceived messages over Mqtt
        // #define MQTT_ONLY_JSON_OUTPUT             false             // [SetOption90] Disable non-json messages
        // #define MQTT_TLS_ENABLED                  false             // [SetOption103] Enable TLS mode
        // #define MQTT_TLS_FINGERPRINT              false             // [SetOption132] Force TLS fingerprint validation instead of CA
        // #define MQTT_TLS_ECDSA                    false             // [SetOption165] Enable TLS ECDSA validation in addition to RSA, false by default but automatically set to 'true' in case of a cipher error '296'
        #ifdef MQTT_MAX_PACKET_SIZE
            #undef MQTT_MAX_PACKET_SIZE
        #endif
        #define MQTT_MAX_PACKET_SIZE                2048                // Bytes - Default is 512, but 1200 is recommended for Home Assistant Discovery and is still well below the maximum of 2048 for ESP32 (MQTT_MAX_PACKET_SIZE must be >= MESSZ)

        // -- FTP Server ---------------------------------------
        #ifdef USE_FTP
            #undef USE_FTP
        #endif
        #define USE_FTP
        #ifdef USE_FTP
            #ifdef USER_FTP
                #undef USER_FTP
            #endif
            #define USER_FTP "fdaubercy"
            #ifdef PW_FTP
                #undef PW_FTP
            #endif
            #define PW_FTP "Lune5676"
        #endif

        // -- Telegram Protocol ---------------------------
        #ifdef USE_TELEGRAM
            #undef USE_TELEGRAM
        #endif
        #define USE_TELEGRAM                             // Support for Telegram protocol (+49k code, +7.0k mem and +4.8k additional during connection handshake)
        #ifdef USE_TELEGRAM
            #ifdef USE_TELEGRAM_FINGERPRINT
                #undef USE_TELEGRAM_FINGERPRINT
            #endif
            #define USE_TELEGRAM_FINGERPRINT "\xB2\x72\x47\xA6\x69\x8C\x3C\x69\xF9\x58\x6C\xF3\x60\x02\xFB\x83\xFA\x8B\x1F\x23" // Telegram api.telegram.org TLS public key fingerpring
        #endif

        // -- mDNS ----------------------------------------
        #ifdef MDNS_ENABLED
            #undef MDNS_ENABLED
        #endif
        #define MDNS_ENABLED      true                   // [SetOption55] Use mDNS (false = Disable, true = Enable)
        
        // -- Time - Up to three NTP servers in your region
        #ifdef NTP_SERVER1
            #undef NTP_SERVER1
        #endif
        #define NTP_SERVER1      "pool.ntp.org"        // [NtpServer1] Select first NTP server by name or IP address (135.125.104.101, 2001:418:3ff::53)
        #ifdef NTP_SERVER2
            #undef NTP_SERVER2
        #endif
        #define NTP_SERVER2      "europe.pool.ntp.org" // [NtpServer2] Select second NTP server by name or IP address (192.36.143.134, 2a00:2381:19c6::100)
        #ifdef NTP_SERVER3
            #undef NTP_SERVER3
        #endif
        #define NTP_SERVER3      "nl.pool.ntp.org"     // [NtpServer3] Select third NTP server by name or IP address (46.249.42.13, 2603:c022:c003:c900::4)

        // -- Time - Start Daylight Saving Time and timezone offset from UTC in minutes
        #ifdef TIME_DST_HEMISPHERE
            #undef TIME_DST_HEMISPHERE
        #endif
        #define TIME_DST_HEMISPHERE    North             // [TimeDst] Hemisphere (0 or North, 1 or South)
        #ifdef TIME_DST_WEEK
            #undef TIME_DST_WEEK
        #endif
        #define TIME_DST_WEEK          Last              // Week of month (0 or Last, 1 or First, 2 or Second, 3 or Third, 4 or Fourth)
        #ifdef TIME_DST_DAY
            #undef TIME_DST_DAY
        #endif
        #define TIME_DST_DAY           Sun               // Day of week (1 or Sun, 2 or Mon, 3 or Tue, 4 or Wed, 5 or Thu, 6 or Fri, 7 or Sat)
        #ifdef TIME_DST_MONTH
            #undef TIME_DST_MONTH
        #endif
        #define TIME_DST_MONTH         Mar               // Month (1 or Jan, 2 or Feb, 3 or Mar, 4 or Apr, 5 or May, 6 or Jun, 7 or Jul, 8 or Aug, 9 or Sep, 10 or Oct, 11 or Nov, 12 or Dec)
        #ifdef TIME_DST_HOUR
            #undef TIME_DST_HOUR
        #endif
        #define TIME_DST_HOUR          2                 // Hour (0 to 23)
        #ifdef TIME_DST_OFFSET
            #undef TIME_DST_OFFSET
        #endif
        #define TIME_DST_OFFSET        +120              // Offset from UTC in minutes (-780 to +780)
        
        // -- Time - Start Standard Time and timezone offset from UTC in minutes
        #ifdef TIME_STD_HEMISPHERE
            #undef TIME_STD_HEMISPHERE
        #endif
        #define TIME_STD_HEMISPHERE    North             // [TimeStd] Hemisphere (0 or North, 1 or South)
        #ifdef TIME_STD_WEEK
            #undef TIME_STD_WEEK
        #endif
        #define TIME_STD_WEEK          Last              // Week of month (0 or Last, 1 or First, 2 or Second, 3 or Third, 4 or Fourth)
        #ifdef TIME_STD_DAY
            #undef TIME_STD_DAY
        #endif
        #define TIME_STD_DAY           Sun               // Day of week (1 or Sun, 2 or Mon, 3 or Tue, 4 or Wed, 5 or Thu, 6 or Fri, 7 or Sat)
        #ifdef TIME_STD_MONTH
            #undef TIME_STD_MONTH
        #endif
        #define TIME_STD_MONTH         Oct               // Month (1 or Jan, 2 or Feb, 3 or Mar, 4 or Apr, 5 or May, 6 or Jun, 7 or Jul, 8 or Aug, 9 or Sep, 10 or Oct, 11 or Nov, 12 or Dec)
        #ifdef TIME_STD_HOUR
            #undef TIME_STD_HOUR
        #endif
        #define TIME_STD_HOUR          3                 // Hour (0 to 23)
        #ifdef TIME_STD_OFFSET
            #undef TIME_STD_OFFSET
        #endif
        #define TIME_STD_OFFSET        +60               // Offset from UTC in minutes (-780 to +780)

        // -- Location ------------------------------------
        #ifdef LATITUDE
            #undef LATITUDE
        #endif
        #define LATITUDE               50.4109163         // [Latitude] Your location to be used with sunrise and sunset
        #ifdef LONGITUDE
            #undef LONGITUDE
        #endif
        #define LONGITUDE              3.0858052          // [Longitude] Your location to be used with sunrise and sunset
        
        // -- Application ---------------------------------
        #ifdef APP_TIMEZONE
            #undef APP_TIMEZONE
        #endif
        #define APP_TIMEZONE            99                  // [Timezone] +1 hour (Amsterdam) (-13 .. 14 = hours from UTC, 99 = use TIME_DST/TIME_STD)
        
        #ifdef MQTT_BUTTONS
            #undef MQTT_BUTTONS
        #endif
        #define MQTT_BUTTONS              true                // [SetOption73] Detach buttons from relays and send multi-press and hold MQTT messages instead
        
        #ifdef MQTT_SWITCHES
            #undef MQTT_SWITCHES
        #endif
        #define MQTT_SWITCHES             true                // [SetOption114] Detach switches from relays and send MQTT messages instead
    #endif  // USER_CONFIG_OVERRIDE_SECTION1

    /*********************************************************************************************\
     * FIN DE LA SECTION 1
     * 
     * SECTION 2
     * - Activer une fonctionnalité en supprimant les deux barres obliques (//) qui la précèdent.
     * - Désactiver une fonctionnalité en la faisant précéder de deux barres obliques (//).
     \*********************************************************************************************/

    #ifdef USER_CONFIG_OVERRIDE_SECTION2
        // -- Localization --------------------------------
        // If non selected the default en-GB will be used
        #ifdef MY_LANGUAGE
            #undef MY_LANGUAGE
        #endif
        #define MY_LANGUAGE            fr_FR           // French in France

        // -- MQTT - Home Assistant Discovery -------------
        #ifdef USE_HOME_ASSISTANT
            #undef USE_HOME_ASSISTANT
        #endif
        #define USE_HOME_ASSISTANT                                   // Enable Home Assistant Discovery Support (+12k code, +6 bytes mem)
        #ifdef USE_HOME_ASSISTANT
            #ifdef HOME_ASSISTANT_DISCOVERY_PREFIX
                #undef HOME_ASSISTANT_DISCOVERY_PREFIX
            #endif
            #define HOME_ASSISTANT_DISCOVERY_PREFIX         "homeassistant"             // Home Assistant discovery prefix
            #ifdef HOME_ASSISTANT_LWT_TOPIC
                #undef HOME_ASSISTANT_LWT_TOPIC
            #endif
            #define HOME_ASSISTANT_LWT_TOPIC                "homeassistant/status"      // home Assistant Birth and Last Will Topic (default = homeassistant/status)
            #ifdef HOME_ASSISTANT_LWT_SUBSCRIBE
                #undef HOME_ASSISTANT_LWT_SUBSCRIBE
            #endif
            #define HOME_ASSISTANT_LWT_SUBSCRIBE            true                        // Subscribe to Home Assistant Birth and Last Will Topic (default = true)
            #ifdef MESSZ
                #undef MESSZ
            #endif
            #define MESSZ                                   2000                        // Max number of characters in JSON message string (Hass discovery and nice MQTT_MAX_PACKET_SIZE = 1200)
        #endif

        // -- MQTT - Tasmota Discovery ---------------------
        #ifdef USE_TASMOTA_DISCOVERY
            #undef USE_TASMOTA_DISCOVERY
        #endif
        #define USE_TASMOTA_DISCOVERY                      // Enable Tasmota Discovery support (+2k code)

        // -- Ping ----------------------------------------
        #ifdef USE_PING
            #undef USE_PING
        #endif
        #define USE_PING                                 // Enable Ping command (+2k code)

        // -- HTTP ----------------------------------------
        #ifdef USE_WEBSERVER
            #undef USE_WEBSERVER
        #endif
        #define USE_WEBSERVER                            // Enable web server and Wi-Fi Manager (+66k code, +8k mem)
        #ifdef USE_WEBSERVER
            #ifdef USE_ENHANCED_GUI_WIFI_SCAN
                #undef USE_ENHANCED_GUI_WIFI_SCAN
            #endif
            #define USE_ENHANCED_GUI_WIFI_SCAN             // Enable Wi-Fi scan output with BSSID (+0k5 code)
            #ifdef USE_WEBSEND_RESPONSE
                #undef USE_WEBSEND_RESPONSE
            #endif
            #define USE_WEBSEND_RESPONSE                   // Enable command WebSend response message (+1k code)
            #ifdef USE_GPIO_VIEWER
                #undef USE_GPIO_VIEWER
            #endif
            #define USE_GPIO_VIEWER                        // Enable GPIO Viewer to see realtime GPIO states (+6k code)
            #ifdef USE_GPIO_VIEWER  
                #ifdef GV_SAMPLING_INTERVAL
                    #undef GV_SAMPLING_INTERVAL
                #endif
                #define GV_SAMPLING_INTERVAL  100            // [GvSampling] milliseconds - Use Tasmota Scheduler (100) or Ticker (20..99,101..1000)
            #endif
            #ifdef USE_WEB_STATUS_LINE
                #undef USE_WEB_STATUS_LINE
            #endif
            #define USE_WEB_STATUS_LINE                      // Enable upper status line in web UI (+0k5 code)
            #ifdef USE_ALPINEJS
                #undef USE_ALPINEJS
            #endif
            #define USE_ALPINEJS                           // Enable AlpineJS v2.8.2 (+8k8 code)
            #ifdef USE_WEBSEND_RESPONSE
                #undef USE_WEBSEND_RESPONSE
            #endif
            #define USE_WEBSEND_RESPONSE                   // Enable command WebSend response message (+1k code)
            #ifdef USE_WEBGETCONFIG
                #undef USE_WEBGETCONFIG
            #endif
            #define USE_WEBGETCONFIG                       // Enable restoring config from external webserver (+0k6)
            #ifdef USE_WEBRUN
                #undef USE_WEBRUN
            #endif
            #define USE_WEBRUN                             // Enable executing a tasmota command file from external web server (+0.4 code)
            #ifdef USE_WEB_STATUS_LINE_WIFI
                #undef USE_WEB_STATUS_LINE_WIFI
            #endif
            #define USE_WEB_STATUS_LINE_WIFI

            // -- mDNS ----------------------------------------
            #ifdef USE_DISCOVERY
                #undef USE_DISCOVERY
            #endif
            #define USE_DISCOVERY                            // Enable mDNS for the following services (+8k code or +23.5k code with core 2_5_x, +0.3k mem)
            #ifdef WEBSERVER_ADVERTISE
                #undef WEBSERVER_ADVERTISE
            #endif
            #define WEBSERVER_ADVERTISE                    // Provide access to webserver by name <Hostname>.local/
            // #define MQTT_HOST_DISCOVERY                    // Find MQTT host server (overrides MQTT_HOST if found) - disabled by default because it causes blocked repeated 3000ms pauses
        #endif
  
        // -- Rules or Script  ----------------------------
        // Select none or only one of the below defines USE_RULES or USE_SCRIPT
        #ifdef USE_SCRIPT
            #undef USE_SCRIPT
        #endif
        // #define USE_SCRIPT                               // Add support for script (+17k code)
        #ifdef USE_SCRIPT
            #ifdef USE_SCRIPT_FATFS
                #undef USE_SCRIPT_FATFS
            #endif
            //#define USE_SCRIPT_FATFS 4                     // Script: Add FAT FileSystem Support
            #ifdef SUPPORT_MQTT_EVENT
                #undef SUPPORT_MQTT_EVENT
            #endif
            #define SUPPORT_MQTT_EVENT                     // Support trigger event with MQTT subscriptions (+3k5 code)
        #endif

        // -- Optional modules ----------------------------
        #ifdef ROTARY_V1
            #undef ROTARY_V1
        #endif
        // #define ROTARY_V1                                // Add support for Rotary Encoder as used in MI Desk Lamp (+0k8 code)
        #ifdef ROTARY_V1
            #ifdef ROTARY_MAX_STEPS
                #undef ROTARY_MAX_STEPS
            #endif
            // #define ROTARY_MAX_STEPS     //10                // Rotary step boundary
        #endif
        #ifdef USE_SONOFF_RF
            #undef USE_SONOFF_RF
        #endif
        // #define USE_SONOFF_RF                            // Add support for Sonoff Rf Bridge (+3k2 code)
        #ifdef USE_SONOFF_RF
            #ifdef USE_RF_FLASH
                #undef USE_RF_FLASH
            #endif
            // #define USE_RF_FLASH                           // Add support for flashing the EFM8BB1 chip on the Sonoff RF Bridge. C2CK must be connected to GPIO4, C2D to GPIO5 on the PCB (+2k7 code)
        #endif
        #ifdef USE_SONOFF_SC
            #undef USE_SONOFF_SC
        #endif
        // #define USE_SONOFF_SC                            // Add support for Sonoff Sc (+1k1 code)
        #ifdef USE_TUYA_MCU
            #undef USE_TUYA_MCU
        #endif
        // #define USE_TUYA_MCU                             // Add support for Tuya Serial MCU
        #ifdef USE_TUYA_MCU
            #ifdef TUYA_DIMMER_ID
                #undef TUYA_DIMMER_ID
            #endif
            // #define TUYA_DIMMER_ID       //0                 // Default dimmer Id
            #ifdef USE_TUYA_TIME
                #undef USE_TUYA_TIME
            #endif
            // #define USE_TUYA_TIME                          // Add support for Set Time in Tuya MCU
        #endif
        #ifdef USE_TUYAMCUBR
            #undef USE_TUYAMCUBR
        #endif
        // #define USE_TUYAMCUBR                            // Add support for TuyaMCU Bridge

        // -- One wire sensors ----------------------------
        #ifdef USE_DS18x20
            #undef USE_DS18x20
        #endif
        // #define USE_DS18x20                              // Add support for DS18x20 sensors with id sort, single scan and read retry (+2k6 code)

        // -- IR Remote features - subset of IR protocols --------------------------
        #ifdef USE_IR_REMOTE
            #undef USE_IR_REMOTE
        #endif
        // #define USE_IR_REMOTE                            // Send IR remote commands using library IRremoteESP8266 (+4k3 code, 0k3 mem, 48 iram)

        #ifdef USE_IR_REMOTE
            // Enable IR devoder via GPIO `IR Recv` - always enabled if `USE_IR_REMOTE_FULL`
            #ifdef USE_IR_RECEIVE
                #undef USE_IR_RECEIVE
            #endif
            #undef USE_IR_RECEIVE                         // Support for IR receiver (+7k2 code, 264 iram)
        #endif

        // -- Other sensors/drivers -----------------------

        /*********************************************************************************************\
            * ESP32 only features
        \*********************************************************************************************/

        #ifdef ESP32
            #define USE_ESP32_SENSORS                        // Add support for ESP32 temperature and optional hall effect sensor
            #define USE_AUTOCONF                             // Enable Esp32 autoconf feature, requires USE_BERRY and USE_WEBCLIENT_HTTPS (12KB Flash)

            #define USE_ESP32_WDT                            // Enable Watchdog for ESP32, trigger a restart if loop has not responded for 5s, and if `yield();` was not called
            #define DEBUG_FUNC_SETTINGSUPDATETEXT           // Enable debug messages for SettingsUpdateText() function
            #define DEBUG_FUNC_SETTINGSUPDATE               // Enable debug messages for SettingsUpdate() function

            // -- Paramètres BERRY ----------------------------
            #ifdef USE_BERRY
                #undef USE_BERRY
            #endif
            #define USE_BERRY                                // Enable Berry scripting language  

            #ifdef USE_BERRY
                #ifdef USE_BERRY_WEBCLIENT_ASYNC
                    #undef USE_BERRY_WEBCLIENT_ASYNC
                #endif
                #define USE_BERRY_WEBCLIENT_ASYNC              // Enable ASYNC webclient mode as an additional mode to standary berry webclient. 
                #ifdef USE_BERRY_PYTHON_COMPAT
                    #undef USE_BERRY_PYTHON_COMPAT
                #endif
                #define USE_BERRY_PYTHON_COMPAT                // Enable by default `import python_compat`
                #ifdef USE_BERRY_TIMEOUT
                    #undef USE_BERRY_TIMEOUT
                #endif
                #define USE_BERRY_TIMEOUT             4000     // Timeout in ms, will raise an exception if running time exceeds this timeout
                #ifdef USE_BERRY_PSRAM
                    #undef USE_BERRY_PSRAM
                #endif
                #define USE_BERRY_PSRAM                        // Allocate Berry memory in PSRAM if PSRAM is connected - this might be slightly slower but leaves main memory intact
                #ifdef USE_BERRY_IRAM
                    #undef USE_BERRY_IRAM
                #endif
                #define USE_BERRY_IRAM                         // Allocate some data structures in IRAM (which is ususally unused) when possible and if no PSRAM is available
                #ifdef USE_BERRY_FAST_LOOP_SLEEP_MS
                    #undef USE_BERRY_FAST_LOOP_SLEEP_MS
                #endif
                #define USE_BERRY_FAST_LOOP_SLEEP_MS  5        // Minimum time in milliseconds to before calling again `tasmota.fast_loop()`, a smaller value will consume more CPU (min 1ms)
                #ifdef USE_BERRY_DEBUG
                    #undef USE_BERRY_DEBUG
                #endif
                //#define USE_BERRY_DEBUG                        // Compile Berry bytecode with line number information, makes exceptions easier to debug. Adds +8% of memory consumption for compiled code
                #ifdef UBE_BERRY_DEBUG_GC
                    #undef UBE_BERRY_DEBUG_GC
                #endif
                //#define UBE_BERRY_DEBUG_GC                   // Print low-level GC metrics
                #ifdef USE_BERRY_INT64
                    #undef USE_BERRY_INT64
                #endif
                #define USE_BERRY_INT64                        // Add 64 bits integer support (+1.7KB Flash)

                #ifdef USE_BERRY_LEDS_PANEL
                    #undef USE_BERRY_LEDS_PANEL
                #endif
                #undef USE_BERRY_LEDS_PANEL
                    // #define USE_BERRY_LEDS_PANEL                 // Add button to dynamically load the Leds Panel from a bec file online
                    // #define USE_BERRY_LEDS_PANEL_URL             "http://ota.tasmota.com/tapp/leds_panel.bec"
                #ifdef USE_BERRY_PARTITION_WIZARD
                    #undef USE_BERRY_PARTITION_WIZARD
                #endif
                //#define USE_BERRY_PARTITION_WIZARD           // Add a button to dynamically load the Partion Wizard from a bec file online (+1.3KB Flash)
                    // #define USE_BERRY_PARTITION_WIZARD_URL      "http://ota.tasmota.com/tapp/partition_wizard.bec"
                    #ifdef USE_BERRY_GPIOVIEWER
                        #undef USE_BERRY_GPIOVIEWER
                    #endif
                    // #define USE_BERRY_GPIOVIEWER                 // Add a button to dynamocally load the GPIO Viewer from a bec file online
                    // #define USE_BERRY_GPIOVIEWER_URL            "http://ota.tasmota.com/tapp/gpioviewer.bec"    // Connect to http: <your_tasmota_ip:5555/
                #ifdef USE_BERRY_TCPSERVER
                    #undef USE_BERRY_TCPSERVER
                #endif
                #define USE_BERRY_TCPSERVER                    // Enable TCP socket server (+0.6k)
                #ifdef USE_BERRY_ULP
                    #undef USE_BERRY_ULP
                #endif
                #define USE_BERRY_ULP                          // Enable ULP (Ultra Low Power) support (+4.9k)
                #ifdef USE_BERRY_MQTTCLIENT
                    #undef USE_BERRY_MQTTCLIENT
                #endif
                #define USE_BERRY_MQTTCLIENT                  // Enable standalone, independent Berry MQTT client (+5.1k)

                #ifdef USE_BERRY_ANIMATION
                    #undef USE_BERRY_ANIMATION
                #endif
                #define USE_BERRY_ANIMATION                     // New animation framework with dedicated language (ESP32x only, experimental, 94k not yet optimized)
                #ifdef USE_BERRY_ANIMATION
                    #ifdef USE_BERRY_ANIMATION_DSL
                        #undef USE_BERRY_ANIMATION_DSL
                    #endif
                    #define USE_BERRY_ANIMATION_DSL             // DSL transpiler for new animation framework (not mandatory if DSL is transpiled externally, +98k not optimized yet)
                #endif
            #endif  // USE_BERRY

            #ifdef USE_SONOFF_SPM
                #undef USE_SONOFF_SPM
            #endif
            #define USE_SONOFF_SPM                           // Add support for ESP32 based Sonoff Smart Stackable Power Meter (+11k code)
        #endif  // ESP32
    #endif  // USER_CONFIG_OVERRIDE_SECTION2

    /*********************************************************************************************\
     * END OF SECTION 2
     *
     * SECTION 3
     * - Firmwares personnalisés
     \*********************************************************************************************/

    #ifdef USER_CONFIG_OVERRIDE_FIRMWARES_PERSONNALISES
        // Nb de GPIO spécifiques à chaque type d'ESP32
        // ESP32 :      36 GPIO -> [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
        // ESP32-S3:    38 GPIO -> [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1]
        // ESP32-P4:    55 GPIO -> [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]

        // -- Options for firmware tasmota32-cave-serveur-rly ------
        #if defined(FIRMWARE_ESP32_CAVE_SERVEUR_RLY)
            // -- CODE_IMAGE_STR is the name shown between brackets on the 
            //    Information page or in INFO MQTT messages
            #undef CODE_IMAGE_STR
            #define CODE_IMAGE_STR "serveur-rly-cave"
        
            // -- Project -------------------------------------
            #undef PROJECT
                #define PROJECT           "SERVEUR-RLY-CAVE"         	 // PROJECT is used as the default topic delimiter
            //#define USER_TEMPLATE "{\"NAME\":\"ESP32 Relay x8\",\"GPIO\":[33,1,160,1,32,1,1,1,1,1,1,161,1,1,34,1,1,1,1216,288,1,226,227,228,1,1,1,1,224,225,1,1,1,1,1,1],\"FLAG\":0,\"BASE\":1}"
            //#define USER_TEMPLATE "{\"NAME\":\"ESP32 Relay x8\",\"GPIO\":[33, 1, 160, 1, 32, 6720, 0, 0, 1, 1, 1, 161, 0, 0, 736, 672, 1, 34, 1216, 704, 1, 226, 227, 228, 0, 0, 0, 0, 224, 225, 1, 1, 1, 1, 1, 1],\"FLAG\":0,\"BASE\":1}"
            // -- Wi-Fi ---------------------------------------
            #undef WIFI_IP_ADDRESS
            #define WIFI_IP_ADDRESS "192.168.0.48" // [IpAddress1] Set to 0.0.0.0 for using DHCP or enter a static IP address
        
            // -- Setup your own Wifi settings  ---------------
            // You might even pass some parameters from the command line ----------------------------
            // Ie:  export PLATFORMIO_BUILD_FLAGS='-DUSE_CONFIG_OVERRIDE -DMY_IP="192.168.1.99" -DMY_GW="192.168.1.1" -DMY_DNS="192.168.1.1"'
        
            // -- Setup your own MQTT settings  ---------------
            #undef MQTT_CLIENT_ID
            #define MQTT_CLIENT_ID "SERVEUR-RLY-CAVE" // [MqttClient] Also fall back topic using last 6 characters of MAC address or use "DVES_%12X" for complete MAC address
            #undef MQTT_TOPIC
            #define MQTT_TOPIC "cave/serveur-rly-cave" // [Topic] unique MQTT device topic including (part of) device MAC address
            #undef MQTT_GRPTOPIC
            #define MQTT_GRPTOPIC "tasmotas/cave" // [GroupTopic] MQTT Group topic
            #undef FRIENDLY_NAME
            #define FRIENDLY_NAME "Serveur Relais Cave" // [FriendlyName] Friendlyname up to 32 characters used by webpages and Alexa
            #undef EMULATION
            #define EMULATION EMUL_NONE // [Emulation] Select Belkin WeMo (single relay/light) or Hue Bridge emulation (multi relay/light) (EMUL_NONE, EMUL_WEMO or EMUL_HUE)
        
            // -- Optional modules ----------------------------
            #undef USE_SHUTTER // Add Shutter support for up to 4 shutter with different motortypes (+11k code)
        
            // -- Internal Analog input -----------------------
            #undef USE_ADC_VCC // Display Vcc in Power status. Disable for use as Analog input on selected devices
        
            // -- LCD I2C -----------------------
            //#define USE_I2C             // I2C using library wire (+10k code, 0k2 mem, 124 iram)
            //#define USE_DISPLAY         // Add I2C/TM1637/MAX7219 Display Support (+2k code)
            //#define USE_DISPLAY_SSD1306 // [DisplayModel 2] [I2cDriver4] Enable SSD1306 Oled 128x64 display (I2C addresses 0x3C and 0x3D) (+16k code)
            //#define USE_DISPLAY_SH1106  // [DisplayModel 7] [I2cDriver6] Enable SH1106 Oled 128x64 display (I2C addresses 0x3C and 0x3D)
            //#define USE_GRAPH           // Enable line charts with displays
            //#define NUM_GRAPHS 4        // Max 16
        
            // -- I2C sensors ---------------------------------
        
            // -- One wire sensors ----------------------------
            #undef USE_HDMI_CEC // Add support for HDMI CEC bus (+7k code, 1456 bytes IRAM)
        
            // -- Rules or Script  ----------------------------
            #ifdef USER_BACKLOG
                #undef USER_BACKLOG
            #endif
            #define USER_BACKLOG      "Backlog Module 0; Hostname SERVEUR-RLY-CAVE"
        
            // -- SPI sensors ---------------------------------
            #define USE_SPI                                  // Hardware SPI using GPIO12(MISO), GPIO13(MOSI) and GPIO14(CLK) in addition to two user selectable GPIOs(CS and DC)
            #ifdef USE_SPI
                #define USE_UFILESYS
                #define GUI_EDIT_FILE
                #define GUI_TRASH_FILE
        
            // -- SD Card support -----------------------------
                #define USE_SDCARD                      // mount SD Card, requires configured SPI pins and setting of `SDCard CS` gpio
                #define SDC_HIDE_INVISIBLES             // hide hidden directories from the SD Card, which prevents crashes when dealing SD created on MacOS
                #define SDCARD_CS_PIN 5                 // Not strictly necessary since the same #define happens in xdrv_50_filesystem.ino
            #endif

        // -- Options for firmware tasmota32-teleinfo-conso ------
        #elif defined(FIRMWARE_TELEINFO_CONSO)
            // -- CODE_IMAGE_STR is the name shown between brackets on the 
            //    Information page or in INFO MQTT messages
            #undef CODE_IMAGE_STR
            #define CODE_IMAGE_STR "teleinfo-conso"
        
            // -- Project -------------------------------------
            #undef PROJECT
                #define PROJECT           "ESP32-TELEINFO"         	 // PROJECT is used as the default topic delimiter
            #define USER_TEMPLATE 		"{\"NAME\":\"Wemos Teleinfo\",\"GPIO\":[1,1,1,1,5664,1,1,1,1,1,1,1,1,1,1376,1,1,640,608,5632,1,1,0,1,0,0,0,1,1,1,1,1,1,1,1,1],\"FLAG\":0,\"BASE\":1}"
        
            // -- Wi-Fi ---------------------------------------
            #undef WIFI_IP_ADDRESS
                #define WIFI_IP_ADDRESS        "0.0.0.0"            // [IpAddress1] Set to 0.0.0.0 for using DHCP or enter a static IP address
        
            // -- Setup your own Wifi settings  ---------------
            // You might even pass some parameters from the command line ----------------------------
            // Ie:  export PLATFORMIO_BUILD_FLAGS='-DUSE_CONFIG_OVERRIDE -DMY_IP="192.168.1.99" -DMY_GW="192.168.1.1" -DMY_DNS="192.168.1.1"'
        
            // -- Setup your own MQTT settings  ---------------
            #undef MQTT_CLIENT_ID
                #define MQTT_CLIENT_ID    "TELEINFO-CONSO"       // [MqttClient] Also fall back topic using last 6 characters of MAC address or use "DVES_%12X" for complete MAC address
            #undef  MQTT_TOPIC
                #define MQTT_TOPIC        "teleinfo/consommation"   		 // [Topic] unique MQTT device topic including (part of) device MAC address
            #undef MQTT_GRPTOPIC
                #define MQTT_GRPTOPIC     "tasmotas"        // [GroupTopic] MQTT Group topic  
            #undef  FRIENDLY_NAME
                #define FRIENDLY_NAME     "TéléInfo Consommation"           // [FriendlyName] Friendlyname up to 32 characters used by webpages and Alexa
            #undef EMULATION
                #define EMULATION         EMUL_NONE               // [Emulation] Select Belkin WeMo (single relay/light) or Hue Bridge emulation (multi relay/light) (EMUL_NONE, EMUL_WEMO or EMUL_HUE)
        
            // -- Optional modules ----------------------------
            #undef USE_SHUTTER                              // Add Shutter support for up to 4 shutter with different motortypes (+11k code)
        
            // -- Internal Analog input -----------------------
            #undef USE_ADC_VCC                              // Display Vcc in Power status. Disable for use as Analog input on selected devices
        
            // -- LCD I2C -----------------------
            #define USE_I2C                                  // I2C using library wire (+10k code, 0k2 mem, 124 iram)
                #define USE_DISPLAY                            // Add I2C/TM1637/MAX7219 Display Support (+2k code)
                    #define USE_DISPLAY_SSD1306                  // [DisplayModel 2] [I2cDriver4] Enable SSD1306 Oled 128x64 display (I2C addresses 0x3C and 0x3D) (+16k code)
                    #define USE_DISPLAY_SH1106                   // [DisplayModel 7] [I2cDriver6] Enable SH1106 Oled 128x64 display (I2C addresses 0x3C and 0x3D)
                    #define USE_GRAPH                            // Enable line charts with displays
                    #define NUM_GRAPHS     4                     // Max 16
        
            // -- I2C sensors ---------------------------------
        
            // -- One wire sensors ----------------------------
            #undef USE_HDMI_CEC                              // Add support for HDMI CEC bus (+7k code, 1456 bytes IRAM)
        
            // -- Power monitoring sensors --------------------
            #define USE_TELEINFO                             // Add support for Teleinfo via serial RX interface (+5k2 code, +168 RAM + SmartMeter LinkedList Values RAM)
        
                // -- Rules or Script  ----------------------------
                #ifdef USER_BACKLOG
                    #undef USER_BACKLOG
                #endif
                #define USER_BACKLOG      "Backlog Module 0; Hostname ESP32-TELEINFO"

        // -- Options for firmware tasmota32-teleinfo-prod ------
        #elif defined(FIRMWARE_TELEINFO_PROD)
            // -- CODE_IMAGE_STR is the name shown between brackets on the 
            //    Information page or in INFO MQTT messages
            #undef CODE_IMAGE_STR
            #define CODE_IMAGE_STR "teleinfo-prod"
        
            // -- Project -------------------------------------
            #undef PROJECT
                #define PROJECT           "ESP32-TELEINFO"         	 // PROJECT is used as the default topic delimiter
            #define USER_TEMPLATE 		"{\"NAME\":\"Wemos Teleinfo\",\"GPIO\":[1,1,1,1,5664,1,1,1,1,1,1,1,1,1,1376,1,1,640,608,5632,1,1,0,1,0,0,0,1,1,1,1,1,1,1,1,1],\"FLAG\":0,\"BASE\":1}"
        
            // -- Wi-Fi ---------------------------------------
            #undef WIFI_IP_ADDRESS
                #define WIFI_IP_ADDRESS        "0.0.0.0"            // [IpAddress1] Set to 0.0.0.0 for using DHCP or enter a static IP address
        
            // -- Setup your own Wifi settings  ---------------
            // You might even pass some parameters from the command line ----------------------------
            // Ie:  export PLATFORMIO_BUILD_FLAGS='-DUSE_CONFIG_OVERRIDE -DMY_IP="192.168.1.99" -DMY_GW="192.168.1.1" -DMY_DNS="192.168.1.1"'
        
            // -- Setup your own MQTT settings  ---------------
            #undef MQTT_CLIENT_ID
                #define MQTT_CLIENT_ID    "TELEINFO-PROD"       // [MqttClient] Also fall back topic using last 6 characters of MAC address or use "DVES_%12X" for complete MAC address
            #undef  MQTT_TOPIC
                #define MQTT_TOPIC        "teleinfo/production"   		 // [Topic] unique MQTT device topic including (part of) device MAC address
            #undef MQTT_GRPTOPIC
                #define MQTT_GRPTOPIC     "tasmotas"        // [GroupTopic] MQTT Group topic  
            #undef  FRIENDLY_NAME
                #define FRIENDLY_NAME     "TéléInfo Production"           // [FriendlyName] Friendlyname up to 32 characters used by webpages and Alexa
            #undef EMULATION
                #define EMULATION         EMUL_NONE               // [Emulation] Select Belkin WeMo (single relay/light) or Hue Bridge emulation (multi relay/light) (EMUL_NONE, EMUL_WEMO or EMUL_HUE)
        
            // -- Optional modules ----------------------------
            #undef USE_SHUTTER                              // Add Shutter support for up to 4 shutter with different motortypes (+11k code)
        
            // -- Internal Analog input -----------------------
            #undef USE_ADC_VCC                              // Display Vcc in Power status. Disable for use as Analog input on selected devices
        
            // -- LCD I2C -----------------------
            #define USE_I2C                                  // I2C using library wire (+10k code, 0k2 mem, 124 iram)
                #define USE_DISPLAY                            // Add I2C/TM1637/MAX7219 Display Support (+2k code)
                    #define USE_DISPLAY_SSD1306                  // [DisplayModel 2] [I2cDriver4] Enable SSD1306 Oled 128x64 display (I2C addresses 0x3C and 0x3D) (+16k code)
                    #define USE_DISPLAY_SH1106                   // [DisplayModel 7] [I2cDriver6] Enable SH1106 Oled 128x64 display (I2C addresses 0x3C and 0x3D)
                    #define USE_GRAPH                            // Enable line charts with displays
                    #define NUM_GRAPHS     4                     // Max 16
        
            // -- I2C sensors ---------------------------------
        
            // -- One wire sensors ----------------------------
            #undef USE_HDMI_CEC                              // Add support for HDMI CEC bus (+7k code, 1456 bytes IRAM)
        
            // -- Power monitoring sensors --------------------
            #define USE_TELEINFO                             // Add support for Teleinfo via serial RX interface (+5k2 code, +168 RAM + SmartMeter LinkedList Values RAM)
        
            // -- Rules or Script  ----------------------------
            #ifdef USER_BACKLOG
                #undef USER_BACKLOG
            #endif
            #define USER_BACKLOG      "Backlog Module 0; Hostname ESP32-TELEINFO"

        // -- Options for firmware tasmota32-rdc-vr-porte ------
        #elif defined(FIRMWARE_ESP32_VR_PORTE)
            // -- CODE_IMAGE_STR is the name shown between brackets on the 
            //    Information page or in INFO MQTT messages
            #undef CODE_IMAGE_STR
            #define CODE_IMAGE_STR "vr-porte"
        
            // -- Project -------------------------------------
            #undef PROJECT
                #define PROJECT           "VR-PORTE"         	 // PROJECT is used as the default topic delimiter
            #define USER_TEMPLATE "{\"NAME\":\"Sonoff Dual R3\",\"GPIO\":[1,1,1,1,1,1,1,1,1,576,224,1,1,1,1,1,0,1,1,1,0,1,1,225,0,0,0,0,160,161,1,1,1,0,0,1],\"FLAG\":0,\"BASE\":1}"
        
            // -- Wi-Fi ---------------------------------------
            #undef WIFI_IP_ADDRESS
            #define WIFI_IP_ADDRESS "192.168.0.46" // [IpAddress1] Set to 0.0.0.0 for using DHCP or enter a static IP address
        
            // -- Setup your own Wifi settings  ---------------
            // You might even pass some parameters from the command line ----------------------------
            // Ie:  export PLATFORMIO_BUILD_FLAGS='-DUSE_CONFIG_OVERRIDE -DMY_IP="192.168.1.99" -DMY_GW="192.168.1.1" -DMY_DNS="192.168.1.1"'
        
            // -- Setup your own MQTT settings  ---------------
            #undef MQTT_CLIENT_ID
            #define MQTT_CLIENT_ID "VR-PORTE" // [MqttClient] Also fall back topic using last 6 characters of MAC address or use "DVES_%12X" for complete MAC address
            #undef MQTT_TOPIC
            #define MQTT_TOPIC "volet/entree" // [Topic] unique MQTT device topic including (part of) device MAC address
            #undef MQTT_GRPTOPIC
            #define MQTT_GRPTOPIC "tasmotas/volets" // [GroupTopic] MQTT Group topic
            #undef FRIENDLY_NAME
            #define FRIENDLY_NAME "Volet de porte d'entrée" // [FriendlyName] Friendlyname up to 32 characters used by webpages and Alexa
            #undef EMULATION
            #define EMULATION EMUL_NONE // [Emulation] Select Belkin WeMo (single relay/light) or Hue Bridge emulation (multi relay/light) (EMUL_NONE, EMUL_WEMO or EMUL_HUE)
        
            // -- Optional modules ----------------------------
            #define USE_SHUTTER // Add Shutter support for up to 4 shutter with different motortypes (+11k code)
        
            // -- Internal Analog input -----------------------
            #undef USE_ADC_VCC // Display Vcc in Power status. Disable for use as Analog input on selected devices
        
            // -- Rules or Script  ----------------------------
            #ifdef USER_BACKLOG
                #undef USER_BACKLOG
            #endif
            #define USER_BACKLOG      "Backlog Module 0; Hostname VR-PORTE"

        // -- Options for firmware tasmota32-serveur-rly-rdc ------
        #elif defined(FIRMWARE_SERVEUR_RLY_RDC)
            // -- CODE_IMAGE_STR is the name shown between brackets on the 
            //    Information page or in INFO MQTT messages
            #undef CODE_IMAGE_STR
            #define CODE_IMAGE_STR "serveur-rly-rdc"
        
            // -- Project -------------------------------------
            #undef PROJECT
                #define PROJECT           "SERVEUR-RLY-RDC"         	 // PROJECT is used as the default topic delimiter
            #define USER_TEMPLATE 		"{\"NAME\":\"ESP32 Relay x8\",\"GPIO\":[33,1,160,1,32,6720,0,0,1,1,1,160,1,1,736,672,1,1216,1,704,1,226,227,228,0,0,0,0,224,225,1,1,1,1,1,1],\"FLAG\":0,\"BASE\":1}"
            // -- Wi-Fi ---------------------------------------
            #undef WIFI_IP_ADDRESS
            #define WIFI_IP_ADDRESS "192.168.0.47" // [IpAddress1] Set to 0.0.0.0 for using DHCP or enter a static IP address
        
            // -- Setup your own Wifi settings  ---------------
            // You might even pass some parameters from the command line ----------------------------
            // Ie:  export PLATFORMIO_BUILD_FLAGS='-DUSE_CONFIG_OVERRIDE -DMY_IP="192.168.1.99" -DMY_GW="192.168.1.1" -DMY_DNS="192.168.1.1"'
        
            // -- Setup your own MQTT settings  ---------------
            #undef MQTT_CLIENT_ID
                #define MQTT_CLIENT_ID "SERVEUR-RLY-RDC" // [MqttClient] Also fall back topic using last 6 characters of MAC address or use "DVES_%12X" for complete MAC address
            #undef MQTT_TOPIC
                #define MQTT_TOPIC "rdc/serveur-rly-rdc" // [Topic] unique MQTT device topic including (part of) device MAC address
            #undef MQTT_GRPTOPIC
                #define MQTT_GRPTOPIC "tasmotas/rdc" // [GroupTopic] MQTT Group topic
            #undef FRIENDLY_NAME
                #define FRIENDLY_NAME "Serveur Relais RdC" // [FriendlyName] Friendlyname up to 32 characters used by webpages and Alexa
            #undef EMULATION
                #define EMULATION EMUL_NONE // [Emulation] Select Belkin WeMo (single relay/light) or Hue Bridge emulation (multi relay/light) (EMUL_NONE, EMUL_WEMO or EMUL_HUE)
            
            // -- Optional modules ----------------------------
            #define USE_SHUTTER // Add Shutter support for up to 4 shutter with different motortypes (+11k code)
        
            // -- Internal Analog input -----------------------
            #undef USE_ADC_VCC // Display Vcc in Power status. Disable for use as Analog input on selected devices	
            
            // -- LCD I2C -----------------------
            #define USE_I2C             // I2C using library wire (+10k code, 0k2 mem, 124 iram)
            //#define USE_DISPLAY         // Add I2C/TM1637/MAX7219 Display Support (+2k code)
            //#define USE_DISPLAY_SSD1306 // [DisplayModel 2] [I2cDriver4] Enable SSD1306 Oled 128x64 display (I2C addresses 0x3C and 0x3D) (+16k code)
            //#define USE_DISPLAY_SH1106  // [DisplayModel 7] [I2cDriver6] Enable SH1106 Oled 128x64 display (I2C addresses 0x3C and 0x3D)
            //#define USE_GRAPH           // Enable line charts with displays
            //#define NUM_GRAPHS 4        // Max 16
        
            // -- I2C sensors ---------------------------------
            // #define I2CDRIVERS_0_31        0xFFFFFFFF        // Enable I2CDriver0  to I2CDriver31
            // #define I2CDRIVERS_32_63       0xFFFFFFFF        // Enable I2CDriver32 to I2CDriver63
            // #define I2CDRIVERS_64_95       0xFFFFFFFF        // Enable I2CDriver64 to I2CDriver95
            // #define I2CDRIVERS_96_127      0xFFFFFFFF        // Enable I2CDriver96 to I2CDriver127
            // #define I2CDRIVERS_128_159     0xFFFFFFFF        // Enable I2CDriver128 to I2CDriver159
        
            // -- One wire sensors ----------------------------
            #undef USE_HDMI_CEC // Add support for HDMI CEC bus (+7k code, 1456 bytes IRAM)
        
            // -- SPI sensors ---------------------------------
            #define USE_SPI                                  // Hardware SPI using GPIO12(MISO), GPIO13(MOSI) and GPIO14(CLK) in addition to two user selectable GPIOs(CS and DC)
            #ifdef USE_SPI
                // -- SD Card support -----------------------------
                #define USE_SDCARD                      // mount SD Card, requires configured SPI pins and setting of `SDCard CS` gpio
                #define SDC_HIDE_INVISIBLES             // hide hidden directories from the SD Card, which prevents crashes when dealing SD created on MacOS
                #define SDCARD_CS_PIN 5                 // Not strictly necessary since the same #define happens in xdrv_50_filesystem.ino
            #endif
        
            // -- ESP-NOW -------------------------------------
            // Plus d'info dans le dossier : "Tasmota\info\xdrv_57_tasmesh.md"
            //#define USE_TASMESH                              // Enable Tasmota Mesh using ESP-NOW (+11k code)
        
            // -- Serial sensors ------------------------------
            //#define USE_SERIAL_BRIDGE                        // Add support for software Serial Bridge (+2k code)
        
            // -- Other sensors/drivers -----------------------
            // GPIO12: 74x595 RClk / GPIO13: 74x595 SRClk / GPIO14: 74x595 Ser
            // Pour utiliser plusieurs 74x595, connecter :
            // - all SRCLK together to GPIO srclk
            // - all RCLK together to GPIO rclk
            // - GPIO ser to SER input of first 74x595
            // - QH' output of first 74x595 to SER input of 2nd 74x595 and so on
            #define USE_SHIFT595                                // Add support for 74xx595 8-bit shift registers (+0k7 code)
            #ifdef USE_SHIFT595
            #define SHIFT595_INVERT_OUTPUTS false             // [SetOption133] Don't invert outputs of 74x595 shift register
            #define SHIFT595_DEVICE_COUNT  1                  // [Shift595DeviceCount] Set the number of connected 74x595 shift registers
            #endif
        
            // Cf. url: https://templates.blakadder.com/dingtian_DT-R008.html
            //#define USE_DINGTIAN
            #ifdef USE_DINGTIAN
            #define USE_DINGTIAN_RELAY                       // Add support for the Dingian board using 74'595 et 74'165 shift registers
            #define DINGTIAN_INPUTS_INVERTED               // Invert input states (Hi => OFF, Low => ON)
            #define DINGTIAN_USE_AS_BUTTON                 // Inputs as Tasmota's virtual Buttons
            #define DINGTIAN_USE_AS_SWITCH                 // Inputs as Tasmota's virtual Switches
            #endif
        
            // -- Rules or Script  ----------------------------
            // Select none or only one of the below defines USE_RULES or USE_SCRIPT
            //#define USE_RULES                                // Add support for rules (+8k code)
            #ifdef USE_RULES
            #define SUPPORT_MQTT_EVENT                     // Support trigger event with MQTT subscriptions (+1k8 code)
            #define USE_EXPRESSION                         // Add support for expression evaluation in rules (+1k7 code)
                #define SUPPORT_IF_STATEMENT                 // Add support for IF statement in rules (+2k7)
            //#define USER_RULE1 "Rule1 on system#boot do meshbroker endon"          // Add rule1 data saved at initial firmware load or when command reset is executed
            //#define USER_RULE2 "<Any rule2 data>"          // Add rule2 data saved at initial firmware load or when command reset is executed
            //#define USER_RULE3 "<Any rule3 data>"          // Add rule3 data saved at initial firmware load or when command reset is executed
            #endif
            #undef USER_BACKLOG
            #define USER_BACKLOG "Backlog Module 0; Hostname SERVEUR-RLY-RDC;"

        // -- Options for firmware tasmota32-serveur-debitmetres-pac ------
        #elif defined(FIRMWARE_SERVEUR_DEBITMETRES_PAC)
            // -- CODE_IMAGE_STR is the name shown between brackets on the 
            //    Information page or in INFO MQTT messages
            #undef CODE_IMAGE_STR
                #define CODE_IMAGE_STR "serveur debitmetres pac"
        
            // -- Project -------------------------------------
            #undef PROJECT
                #define PROJECT           "SERVEUR-DEBITMETRES-PAC"         	 // PROJECT is used as the default topic delimiter
                #define USER_TEMPLATE 		"{\"NAME\":\"ESP32 Debitmetres PAC\",\"GPIO\":[1,1,1,1,1,6720,1,1,1,1,1,1,1,1,736,672,1,1,1,704,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],\"FLAG\":0,\"BASE\":1}"
                
            // -- Wi-Fi ---------------------------------------
            #undef WIFI_IP_ADDRESS
                #define WIFI_IP_ADDRESS "192.168.0.43" // [IpAddress1] Set to 0.0.0.0 for using DHCP or enter a static IP address
                
            // You might even pass some parameters from the command line ----------------------------
            // Ie:  export PLATFORMIO_BUILD_FLAGS='-DUSE_CONFIG_OVERRIDE -DMY_IP="192.168.1.99" -DMY_GW="192.168.1.1" -DMY_DNS="192.168.1.1"'
        
            #undef WIFI_CONFIG_TOOL
                #define WIFI_CONFIG_TOOL       WIFI_RETRY         // [WifiConfig] Default tool if Wi-Fi fails to connect (default option: 4 - WIFI_RETRY)
                                                                    // (0=WIFI_RESTART, 2=WIFI_MANAGER, 4=WIFI_RETRY, 5=WIFI_WAIT, 6=WIFI_SERIAL, 7=WIFI_MANAGER_RESET_ONLY)
        
            // -- Setup your own RANGE EXTENDER settings  -----
            // Les autres paramètres du RangeExtender sont gérés par la partie 'Post-process compile options' en fin de fichier
            // Backlog RgxSSID rangeextender ; RgxPassword securepassword ; RgxAddress 192.168.123.1 ; RgxSubnet 255.255.255.0; RgxState 1 ; RgxNAPT 1
            #define USE_WIFI_RANGE_EXTENDER
                #define WIFI_RGX_SSID           "SERVEUR-DEBITMETRES-PAC-AP"
                #define WIFI_RGX_PASSWORD       "Lune5676"
            
            // -- Setup your own MQTT settings  ---------------
            #undef MQTT_CLIENT_ID
                #define MQTT_CLIENT_ID "DEBITMETRES-PAC" // [MqttClient] Also fall back topic using last 6 characters of MAC address or use "DVES_%12X" for complete MAC address
            #undef MQTT_TOPIC
                #define MQTT_TOPIC "pac/debitmetres" // [Topic] unique MQTT device topic including (part of) device MAC address
            #undef MQTT_GRPTOPIC
                #define MQTT_GRPTOPIC "tasmotas/pac" // [GroupTopic] MQTT Group topic
            #undef FRIENDLY_NAME
                #define FRIENDLY_NAME "Débitmètres PAC" // [FriendlyName] Friendlyname up to 32 characters used by webpages and Alexa
            #undef EMULATION
                #define EMULATION EMUL_NONE // [Emulation] Select Belkin WeMo (single relay/light) or Hue Bridge emulation (multi relay/light) (EMUL__NONE, EMUL_WEMO or EMUL_HUE)
            
            // -- Optional modules ----------------------------
            #undef USE_SHUTTER // Add Shutter support for up to 4 shutter with different motortypes (+11k code)
        
            // -- Internal Analog input -----------------------
            #undef USE_ADC_VCC // Display Vcc in Power status. Disable for use as Analog input on selected devices	
        
            // -- Optional light modules ----------------------
            #undef USE_WS2812                               // WS2812 Led string using library NeoPixelBus (+5k code, +1k mem, 232 iram) - Disable by //
                #undef USE_WS2812_HARDWARE  //NEO_HW_WS2812     // Hardware type (NEO_HW_WS2812, NEO_HW_WS2812X, NEO_HW_WS2813, NEO_HW_SK6812, NEO_HW_LC8812, NEO_HW_APA106, NEO_HW_P9813)
                #undef  USE_WS2812_CTYPE     //NEO_GRB           // Color type (NEO_RGB, NEO_GRB, NEO_BRG, NEO_RBG, NEO_RGBW, NEO_GRBW)
            
            // -- LCD I2C -----------------------
            #define USE_I2C             // I2C using library wire (+10k code, 0k2 mem, 124 iram)
            //#define USE_DISPLAY         // Add I2C/TM1637/MAX7219 Display Support (+2k code)
            //#define USE_DISPLAY_SSD1306 // [DisplayModel 2] [I2cDriver4] Enable SSD1306 Oled 128x64 display (I2C addresses 0x3C and 0x3D) (+16k code)
            //#define USE_DISPLAY_SH1106  // [DisplayModel 7] [I2cDriver6] Enable SH1106 Oled 128x64 display (I2C addresses 0x3C and 0x3D)
            //#define USE_GRAPH           // Enable line charts with displays
            //#define NUM_GRAPHS 4        // Max 16
        
                // -- I2C sensors ---------------------------------
            #define I2CDRIVERS_0_31        0xFFFFFFFF        // Enable I2CDriver0  to I2CDriver31
            #define I2CDRIVERS_32_63       0xFFFFFFFF        // Enable I2CDriver32 to I2CDriver63
            #define I2CDRIVERS_64_95       0xFFFFFFFF        // Enable I2CDriver64 to I2CDriver95
            #define I2CDRIVERS_96_127      0xFFFFFFFF        // Enable I2CDriver96 to I2CDriver127
            #define I2CDRIVERS_128_159     0xFFFFFFFF        // Enable I2CDriver128 to I2CDriver159
        
            // -- SPI sensors ---------------------------------
            #define USE_SPI                                  // Hardware SPI using GPIO12(MISO), GPIO13(MOSI) and GPIO14(CLK) in addition to two user selectable GPIOs(CS and DC)
                #define USE_ILI9488                            // Utilisation de l'ecran ILI9488. Les autres paramètres pour ILI9488 sont gérés par la partie 'Post-process compile options' en fin de fichier  
        
            // -- One wire sensors ----------------------------
            #undef USE_HDMI_CEC                              // Add support for HDMI CEC bus (+7k code, 1456 bytes IRAM)
        
            // -- Serial sensors ------------------------------
            //#define USE_SERIAL_BRIDGE                        // Add support for software Serial Bridge (+2k code)
        
            // -- Other sensors/drivers -----------------------
            // GPIO12: 74x595 RClk / GPIO13: 74x595 SRClk / GPIO14: 74x595 Ser
            // Pour utiliser plusieurs 74x595, connecter :
            // - all SRCLK together to GPIO srclk
            // - all RCLK together to GPIO rclk
            // - GPIO ser to SER input of first 74x595
            // - QH' output of first 74x595 to SER input of 2nd 74x595 and so on
            //#define USE_SHIFT595                                // Add support for 74xx595 8-bit shift registers (+0k7 code)
            #ifdef USE_SHIFT595
                #define SHIFT595_INVERT_OUTPUTS false             // [SetOption133] Don't invert outputs of 74x595 shift register
                #define SHIFT595_DEVICE_COUNT  1                  // [Shift595DeviceCount] Set the number of connected 74x595 shift registers
            #endif
        
            // Cf. url: https://templates.blakadder.com/dingtian_DT-R008.html
            //#define USE_DINGTIAN
            #ifdef USE_DINGTIAN
                #define USE_DINGTIAN_RELAY                       // Add support for the Dingian board using 74'595 et 74'165 shift registers
                #define DINGTIAN_INPUTS_INVERTED               // Invert input states (Hi => OFF, Low => ON)
                #define DINGTIAN_USE_AS_BUTTON                 // Inputs as Tasmota's virtual Buttons
                #define DINGTIAN_USE_AS_SWITCH                 // Inputs as Tasmota's virtual Switches
            #endif
        
            // -- Rules or Script  ----------------------------
            // Select none or only one of the below defines USE_RULES or USE_SCRIPT
            #define USE_RULES                                // Add support for rules (+8k code)
            #ifdef USE_RULES
                #define SUPPORT_MQTT_EVENT                     // Support trigger event with MQTT subscriptions (+1k8 code)
                #define USE_EXPRESSION                         // Add support for expression evaluation in rules (+1k7 code)
                    #define SUPPORT_IF_STATEMENT                 // Add support for IF statement in rules (+2k7)
                //#define USER_RULE1 "ON System#Boot DO RgxPort tcp, 8080, 10.99.0.2, 80 ENDON"          // Add rule1 data saved at initial firmware load or when command reset is executed
                //#define USER_RULE2 "<Any rule2 data>"          // Add rule2 data saved at initial firmware load or when command reset is executed
                //#define USER_RULE3 "<Any rule3 data>"          // Add rule3 data saved at initial firmware load or when command reset is executed
            #endif
            #ifdef USER_BACKLOG
                #undef USER_BACKLOG
            #endif
            #define USER_BACKLOG      "Backlog Module 0; Hostname SERVEUR-DEBITMETRES-PAC"

        // -- Options for tasmota32-rideau-garage-modbus ------
        #elif defined(FIRMWARE_ESP32S3_SERVEUR_DEBITMETRES_PAC)
            // -- CODE_IMAGE_STR is the name shown between brackets on the 
            //    Information page or in INFO MQTT messages
            #undef CODE_IMAGE_STR
                #define CODE_IMAGE_STR "serveur debitmetres pac"
        
            // -- Project -------------------------------------
            #undef PROJECT
                #define PROJECT           "SERVEUR-DEBITMETRES-PAC"         	 // PROJECT is used as the default topic delimiter
                #define USER_TEMPLATE 		"{\"NAME\":\"ESP32S3 Debitmetres PAC\",\"GPIO\":[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,288,544,1,1,1,1,1,1,1,1,1376],\"FLAG\":0,\"BASE\":1}"
            // -- Wi-Fi ---------------------------------------
            #undef WIFI_IP_ADDRESS
                #define WIFI_IP_ADDRESS "192.168.0.43" // [IpAddress1] Set to 0.0.0.0 for using DHCP or enter a static IP address
                
            // You might even pass some parameters from the command line ----------------------------
            // Ie:  export PLATFORMIO_BUILD_FLAGS='-DUSE_CONFIG_OVERRIDE -DMY_IP="192.168.1.99" -DMY_GW="192.168.1.1" -DMY_DNS="192.168.1.1"'
        
            #undef WIFI_CONFIG_TOOL
                #define WIFI_CONFIG_TOOL       WIFI_RETRY         // [WifiConfig] Default tool if Wi-Fi fails to connect (default option: 4 - WIFI_RETRY)
                                                                    // (0=WIFI_RESTART, 2=WIFI_MANAGER, 4=WIFI_RETRY, 5=WIFI_WAIT, 6=WIFI_SERIAL, 7=WIFI_MANAGER_RESET_ONLY)
        
            // -- Setup your own RANGE EXTENDER settings  -----
            // Les autres paramètres du RangeExtender sont gérés par la partie 'Post-process compile options' en fin de fichier
            // Backlog RgxSSID rangeextender ; RgxPassword securepassword ; RgxAddress 192.168.123.1 ; RgxSubnet 255.255.255.0; RgxState 1 ; RgxNAPT 1
            #define USE_WIFI_RANGE_EXTENDER
                #define WIFI_RGX_SSID           "SERVEUR-DEBITMETRES-PAC-AP"
                #define WIFI_RGX_PASSWORD       "Lune5676"
            
            // -- Setup your own MQTT settings  ---------------
            #undef MQTT_CLIENT_ID
                #define MQTT_CLIENT_ID "SERVEUR-DEBITMETRES-PAC" // [MqttClient] Also fall back topic using last 6 characters of MAC address or use "DVES_%12X" for complete MAC address
            #undef MQTT_TOPIC
                #define MQTT_TOPIC "pac/debitmetres" // [Topic] unique MQTT device topic including (part of) device MAC address
            #undef MQTT_GRPTOPIC
                #define MQTT_GRPTOPIC "tasmotas/pac" // [GroupTopic] MQTT Group topic
            #undef FRIENDLY_NAME
                #define FRIENDLY_NAME "Débitmètres PAC" // [FriendlyName] Friendlyname up to 32 characters used by webpages and Alexa
            #undef EMULATION
                #define EMULATION EMUL_NONE // [Emulation] Select Belkin WeMo (single relay/light) or Hue Bridge emulation (multi relay/light) (EMUL__NONE, EMUL_WEMO or EMUL_HUE)
            
            // -- Optional modules ----------------------------
            #undef USE_SHUTTER // Add Shutter support for up to 4 shutter with different motortypes (+11k code)
        
            // -- Internal Analog input -----------------------
            #undef USE_ADC_VCC // Display Vcc in Power status. Disable for use as Analog input on selected devices	
        
            // -- Optional light modules ----------------------
            #define USE_LIGHT                                // Add support for light control
            #define USE_WS2812                               // WS2812 Led string using library NeoPixelBus (+5k code, +1k mem, 232 iram) - Disable by //
            //  #define USE_WS2812_DMA                         // ESP8266 only, DMA supports only GPIO03 (= Serial RXD) (+1k mem). When USE_WS2812_DMA is enabled expect Exceptions on Pow
                #define USE_WS2812_RMT  0                      // ESP32 only, hardware RMT support (default). Specify the RMT channel 0..7. This should be preferred to software bit bang.
            //  #define USE_WS2812_I2S  0                      // ESP32 only, hardware I2S support. Specify the I2S channel 0..2. This is exclusive from RMT. By default, prefer RMT support
            //  #define USE_WS2812_INVERTED                    // Use inverted data signal
                #define USE_WS2812_HARDWARE  NEO_HW_WS2812     // Hardware type (NEO_HW_WS2812, NEO_HW_WS2812X, NEO_HW_WS2813, NEO_HW_SK6812, NEO_HW_LC8812, NEO_HW_APA106, NEO_HW_P9813)
                #undef USE_WS2812_CTYPE
                #define USE_WS2812_CTYPE     NEO_GRB           // Color type (NEO_RGB, NEO_GRB, NEO_BRG, NEO_RBG, NEO_RGBW, NEO_GRBW)
            
            // -- I2C -----------------------
            #define USE_I2C             // I2C using library wire (+10k code, 0k2 mem, 124 iram)
            #ifdef USE_I2C
                // -- LCD I2C -----------------------
                //#define USE_DISPLAY         // Add I2C/TM1637/MAX7219 Display Support (+2k code)
                //#define USE_DISPLAY_SSD1306 // [DisplayModel 2] [I2cDriver4] Enable SSD1306 Oled 128x64 display (I2C addresses 0x3C and 0x3D) (+16k code)
                //#define USE_DISPLAY_SH1106  // [DisplayModel 7] [I2cDriver6] Enable SH1106 Oled 128x64 display (I2C addresses 0x3C and 0x3D)
                //#define USE_GRAPH           // Enable line charts with displays
                //#define NUM_GRAPHS 4        // Max 16
        
                // -- I2C sensors ---------------------------------
                #define I2CDRIVERS_0_31        0xFFFFFFFF        // Enable I2CDriver0  to I2CDriver31
                #define I2CDRIVERS_32_63       0xFFFFFFFF        // Enable I2CDriver32 to I2CDriver63
                #define I2CDRIVERS_64_95       0xFFFFFFFF        // Enable I2CDriver64 to I2CDriver95
                #define I2CDRIVERS_96_127      0xFFFFFFFF        // Enable I2CDriver96 to I2CDriver127
                #define I2CDRIVERS_128_159     0xFFFFFFFF        // Enable I2CDriver128 to I2CDriver159
        
                // Cf. url: https://tasmota.github.io/docs/MCP230xx/
                // Vérifier activation du driver : I2cDriver22 1
                // Tester l'adresse du module MCP23XXX (adresse comprise entre 0x20 & 0x26) : I2CScan
                // Les paramètres des I/O est realisé dans le fichier mcp23xx.dat
                // Paramètres Mode 2 MCP23017
                // #define USE_MCP23XXX_DRV
        
                // Paramètres Mode 1 MCP23017 (mode lancé si echec activation mode 2)
                #ifdef USE_MCP23XXX_DRV
                    #define USE_MCP230xx                            // [I2cDriver22] Enable MCP23008/MCP23017 - Must define I2C Address in #define USE_MCP230xx_ADDR below - range 0x20 - 0x27 (+5k1 code)
                    #define USE_MCP230xx_ADDR 0x20                  // Enable MCP23008/MCP23017 I2C Address to use (Must be within range 0x20 through 0x26 - set according to your wired setup)
                    #define USE_MCP230xx_OUTPUT                     // Enable MCP23008/MCP23017 OUTPUT support through sensor29 commands (+2k2 code)
                    #define USE_MCP230xx_DISPLAYOUTPUT              // Enable MCP23008/MCP23017 to display state of OUTPUT pins on Web UI (+0k2 code)
                #endif
            #endif
        
            // -- SPI sensors ---------------------------------
            #define USE_SPI                                  // Hardware SPI using GPIO12(MISO), GPIO13(MOSI) and GPIO14(CLK) in addition to two user selectable GPIOs(CS and DC)
                //#define USE_ILI9488                            // Utilisation de l'ecran ILI9488. Les autres paramètres pour ILI9488 sont gérés par la partie 'Post-process compile options' en fin de fichier
        
            // -- One wire sensors ----------------------------
            #undef USE_HDMI_CEC                              // Add support for HDMI CEC bus (+7k code, 1456 bytes IRAM)
        
            // -- Serial sensors ------------------------------
            #define USE_SERIAL_BRIDGE                        // Add support for software Serial Bridge (+2k code)
            #define USE_TCP_BRIDGE                           //  Add support for Serial to TCP bridge (+1.3k code)
        
            // -- Other sensors/drivers -----------------------
            // GPIO12: 74x595 RClk / GPIO13: 74x595 SRClk / GPIO14: 74x595 Ser
            // Pour utiliser plusieurs 74x595, connecter :
            // - all SRCLK together to GPIO srclk
            // - all RCLK together to GPIO rclk
            // - GPIO ser to SER input of first 74x595
            // - QH' output of first 74x595 to SER input of 2nd 74x595 and so on
            //#define USE_SHIFT595                                // Add support for 74xx595 8-bit shift registers (+0k7 code)
            #ifdef USE_SHIFT595
                #define SHIFT595_INVERT_OUTPUTS false             // [SetOption133] Don't invert outputs of 74x595 shift register
                #define SHIFT595_DEVICE_COUNT  1                  // [Shift595DeviceCount] Set the number of connected 74x595 shift registers
            #endif
        
            // Cf. url: https://templates.blakadder.com/dingtian_DT-R008.html
            //#define USE_DINGTIAN
            #ifdef USE_DINGTIAN
                #define USE_DINGTIAN_RELAY                       // Add support for the Dingian board using 74'595 et 74'165 shift registers
                #define DINGTIAN_INPUTS_INVERTED               // Invert input states (Hi => OFF, Low => ON)
                #define DINGTIAN_USE_AS_BUTTON                 // Inputs as Tasmota's virtual Buttons
                #define DINGTIAN_USE_AS_SWITCH                 // Inputs as Tasmota's virtual Switches
            #endif
            
            // -- Rules or Script  ----------------------------
            // Select none or only one of the below defines USE_RULES or USE_SCRIPT
            #define USE_RULES                                // Add support for rules (+8k code)
            #ifdef USE_RULES
                #define SUPPORT_MQTT_EVENT                     // Support trigger event with MQTT subscriptions (+1k8 code)
                #define USE_EXPRESSION                         // Add support for expression evaluation in rules (+1k7 code)
                    #define SUPPORT_IF_STATEMENT                 // Add support for IF statement in rules (+2k7)
                //#define USER_RULE1 "<Any rule1 data>"          // Add rule1 data saved at initial firmware load or when command reset is executed
                //#define USER_RULE2 "<Any rule2 data>"          // Add rule2 data saved at initial firmware load or when command reset is executed
                //#define USER_RULE3 "<Any rule3 data>"          // Add rule3 data saved at initial firmware load or when command reset is executed
            #endif
            #ifdef USER_BACKLOG
                #undef USER_BACKLOG
            #endif
            #define USER_BACKLOG      "Backlog Module 0; Hostname SERVEUR-DEBITMETRES-PAC"

        // -- Options for firmware tasmota32-lcd-serveur-debitmetres-pac ------
        #elif defined(FIRMWARE_ESP32S3_LCD_SERVEUR_DEBITMETRES_PAC)
            // -- CODE_IMAGE_STR is the name shown between brackets on the 
            //    Information page or in INFO MQTT messages
            #undef CODE_IMAGE_STR
                #define CODE_IMAGE_STR "ili9488 pac"
        
            // -- Project -------------------------------------
            #undef PROJECT
                #define PROJECT           "ILI9488-PAC"         	 // PROJECT is used as the default topic delimiter
                #define USER_TEMPLATE 		"{\"NAME\":\"ESP32S3 ILI8499\",\"GPIO\":[6210,1,1,11008,992,1,1024,800,1,7264,768,704,736,672,1,1,1,1,1,1,1,1,1,1,1,1,1,288,544,1,1,1,1,1,1,1,1,1376],\"FLAG\":0,\"BASE\":1}"
            // -- Wi-Fi ---------------------------------------
            #undef WIFI_IP_ADDRESS
                #define WIFI_IP_ADDRESS       "10.99.0.3"         // [IpAddress1] Set to 0.0.0.0 for using DHCP or enter a static IP address
            #undef WIFI_GATEWAY
                #define WIFI_GATEWAY           "10.99.0.1"      // [IpAddress2] If not using DHCP set Gateway IP address
                
            // You might even pass some parameters from the command line ----------------------------
            // Ie:  export PLATFORMIO_BUILD_FLAGS='-DUSE_CONFIG_OVERRIDE -DMY_IP="192.168.1.99" -DMY_GW="192.168.1.1" -DMY_DNS="192.168.1.1"'
        
            #undef WIFI_CONFIG_TOOL
                #define WIFI_CONFIG_TOOL       WIFI_MANAGER         // [WifiConfig] Default tool if Wi-Fi fails to connect (default option: 4 - WIFI_RETRY)
                                                                    // (0=WIFI_RESTART, 2=WIFI_MANAGER, 4=WIFI_RETRY, 5=WIFI_WAIT, 6=WIFI_SERIAL, 7=WIFI_MANAGER_RESET_ONLY)
            
            // -- Setup your own MQTT settings  ---------------
            #undef MQTT_CLIENT_ID
                #define MQTT_CLIENT_ID "ILI9488-PAC" // [MqttClient] Also fall back topic using last 6 characters of MAC address or use "DVES_%12X" for complete MAC address
            #undef MQTT_TOPIC
                #define MQTT_TOPIC "pac/ili8499" // [Topic] unique MQTT device topic including (part of) device MAC address
            #undef MQTT_GRPTOPIC
                #define MQTT_GRPTOPIC "tasmotas/pac" // [GroupTopic] MQTT Group topic
            #undef FRIENDLY_NAME
                #define FRIENDLY_NAME "Ecran ILI9488 PAC" // [FriendlyName] Friendlyname up to 32 characters used by webpages and Alexa
            #undef EMULATION
                #define EMULATION EMUL_NONE // [Emulation] Select Belkin WeMo (single relay/light) or Hue Bridge emulation (multi relay/light) (EMUL__NONE, EMUL_WEMO or EMUL_HUE)
            
            // -- Optional modules ----------------------------
            #undef USE_SHUTTER // Add Shutter support for up to 4 shutter with different motortypes (+11k code)
        
            // -- Internal Analog input -----------------------
            #undef USE_ADC_VCC // Display Vcc in Power status. Disable for use as Analog input on selected devices	
        
            // -- Optional light modules ----------------------
            #define USE_LIGHT                                // Add support for light control
            #define USE_WS2812                               // WS2812 Led string using library NeoPixelBus (+5k code, +1k mem, 232 iram) - Disable by //
            //  #define USE_WS2812_DMA                         // ESP8266 only, DMA supports only GPIO03 (= Serial RXD) (+1k mem). When USE_WS2812_DMA is enabled expect Exceptions on Pow
                #define USE_WS2812_RMT  0                      // ESP32 only, hardware RMT support (default). Specify the RMT channel 0..7. This should be preferred to software bit bang.
            //  #define USE_WS2812_I2S  0                      // ESP32 only, hardware I2S support. Specify the I2S channel 0..2. This is exclusive from RMT. By default, prefer RMT support
            //  #define USE_WS2812_INVERTED                    // Use inverted data signal
                #define USE_WS2812_HARDWARE  NEO_HW_WS2812     // Hardware type (NEO_HW_WS2812, NEO_HW_WS2812X, NEO_HW_WS2813, NEO_HW_SK6812, NEO_HW_LC8812, NEO_HW_APA106, NEO_HW_P9813)
                #undef USE_WS2812_CTYPE
                #define USE_WS2812_CTYPE     NEO_GRB           // Color type (NEO_RGB, NEO_GRB, NEO_BRG, NEO_RBG, NEO_RGBW, NEO_GRBW)
            
            // -- I2C -----------------------
            #define USE_I2C             // I2C using library wire (+10k code, 0k2 mem, 124 iram)
            #ifdef USE_I2C
                // -- LCD I2C -----------------------
                //#define USE_DISPLAY         // Add I2C/TM1637/MAX7219 Display Support (+2k code)
                //#define USE_DISPLAY_SSD1306 // [DisplayModel 2] [I2cDriver4] Enable SSD1306 Oled 128x64 display (I2C addresses 0x3C and 0x3D) (+16k code)
                //#define USE_DISPLAY_SH1106  // [DisplayModel 7] [I2cDriver6] Enable SH1106 Oled 128x64 display (I2C addresses 0x3C and 0x3D)
                //#define USE_GRAPH           // Enable line charts with displays
                //#define NUM_GRAPHS 4        // Max 16
        
                // -- I2C sensors ---------------------------------
                #define I2CDRIVERS_0_31        0xFFFFFFFF        // Enable I2CDriver0  to I2CDriver31
                #define I2CDRIVERS_32_63       0xFFFFFFFF        // Enable I2CDriver32 to I2CDriver63
                #define I2CDRIVERS_64_95       0xFFFFFFFF        // Enable I2CDriver64 to I2CDriver95
                #define I2CDRIVERS_96_127      0xFFFFFFFF        // Enable I2CDriver96 to I2CDriver127
                #define I2CDRIVERS_128_159     0xFFFFFFFF        // Enable I2CDriver128 to I2CDriver159
        
                // Cf. url: https://tasmota.github.io/docs/MCP230xx/
                // Vérifier activation du driver : I2cDriver22 1
                // Tester l'adresse du module MCP23XXX (adresse comprise entre 0x20 & 0x26) : I2CScan
                // Les paramètres des I/O est realisé dans le fichier mcp23xx.dat
                // Paramètres Mode 2 MCP23017
                // #define USE_MCP23XXX_DRV
        
                // Paramètres Mode 1 MCP23017 (mode lancé si echec activation mode 2)
                #ifdef USE_MCP23XXX_DRV
                    #define USE_MCP230xx                            // [I2cDriver22] Enable MCP23008/MCP23017 - Must define I2C Address in #define USE_MCP230xx_ADDR below - range 0x20 - 0x27 (+5k1 code)
                    #define USE_MCP230xx_ADDR 0x20                  // Enable MCP23008/MCP23017 I2C Address to use (Must be within range 0x20 through 0x26 - set according to your wired setup)
                    #define USE_MCP230xx_OUTPUT                     // Enable MCP23008/MCP23017 OUTPUT support through sensor29 commands (+2k2 code)
                    #define USE_MCP230xx_DISPLAYOUTPUT              // Enable MCP23008/MCP23017 to display state of OUTPUT pins on Web UI (+0k2 code)
                #endif
            #endif
        
            // -- SPI sensors ---------------------------------
            #define USE_SPI                                  // Hardware SPI using GPIO12(MISO), GPIO13(MOSI) and GPIO14(CLK) in addition to two user selectable GPIOs(CS and DC)
                #define USE_ILI9488                            // Utilisation de l'ecran ILI9488. Les autres paramètres pour ILI9488 sont gérés par la partie 'Post-process compile options' en fin de fichier
        
            // -- One wire sensors ----------------------------
            #undef USE_HDMI_CEC                              // Add support for HDMI CEC bus (+7k code, 1456 bytes IRAM)
        
            // -- Serial sensors ------------------------------
            #define USE_SERIAL_BRIDGE                        // Add support for software Serial Bridge (+2k code)
            #define USE_TCP_BRIDGE                           //  Add support for Serial to TCP bridge (+1.3k code)
        
            // -- Other sensors/drivers -----------------------
            // GPIO12: 74x595 RClk / GPIO13: 74x595 SRClk / GPIO14: 74x595 Ser
            // Pour utiliser plusieurs 74x595, connecter :
            // - all SRCLK together to GPIO srclk
            // - all RCLK together to GPIO rclk
            // - GPIO ser to SER input of first 74x595
            // - QH' output of first 74x595 to SER input of 2nd 74x595 and so on
            //#define USE_SHIFT595                                // Add support for 74xx595 8-bit shift registers (+0k7 code)
            #ifdef USE_SHIFT595
                #define SHIFT595_INVERT_OUTPUTS false             // [SetOption133] Don't invert outputs of 74x595 shift register
                #define SHIFT595_DEVICE_COUNT  1                  // [Shift595DeviceCount] Set the number of connected 74x595 shift registers
            #endif
        
            // Cf. url: https://templates.blakadder.com/dingtian_DT-R008.html
            //#define USE_DINGTIAN
            #ifdef USE_DINGTIAN
                #define USE_DINGTIAN_RELAY                       // Add support for the Dingian board using 74'595 et 74'165 shift registers
                #define DINGTIAN_INPUTS_INVERTED               // Invert input states (Hi => OFF, Low => ON)
                #define DINGTIAN_USE_AS_BUTTON                 // Inputs as Tasmota's virtual Buttons
                #define DINGTIAN_USE_AS_SWITCH                 // Inputs as Tasmota's virtual Switches
            #endif
            
            // -- Rules or Script  ----------------------------
            // Select none or only one of the below defines USE_RULES or USE_SCRIPT
            #define USE_RULES                                // Add support for rules (+8k code)
            #ifdef USE_RULES
                #define SUPPORT_MQTT_EVENT                     // Support trigger event with MQTT subscriptions (+1k8 code)
                #define USE_EXPRESSION                         // Add support for expression evaluation in rules (+1k7 code)
                    #define SUPPORT_IF_STATEMENT                 // Add support for IF statement in rules (+2k7)
                //#define USER_RULE1 "<Any rule1 data>"          // Add rule1 data saved at initial firmware load or when command reset is executed
                //#define USER_RULE2 "<Any rule2 data>"          // Add rule2 data saved at initial firmware load or when command reset is executed
                //#define USER_RULE3 "<Any rule3 data>"          // Add rule3 data saved at initial firmware load or when command reset is executed
            #endif
            #ifdef USER_BACKLOG
                #undef USER_BACKLOG
            #endif
            #define USER_BACKLOG      "Backlog Module 0; Hostname ILI9488-PAC"

        // -- Options for firmware tasmota32-debitmetres-pac1 ------
        #elif defined(FIRMWARE_DEBITMETRES_PAC1)
            // -- CODE_IMAGE_STR is the name shown between brackets on the 
            //    Information page or in INFO MQTT messages
            #undef CODE_IMAGE_STR
                #define CODE_IMAGE_STR "debitmetres pac"
        
            // -- Project -------------------------------------
            #undef PROJECT
                #define PROJECT           "DEBITMETRES-PAC"         	 // PROJECT is used as the default topic delimiter
                #define USER_TEMPLATE 		"{\"NAME\":\"ESP32 Debitmetres PAC\",\"GPIO\":[1,1,1,1,1,1,0,0,1,1,1,1,0,0,1,1,1,1,1,1,1,8992,8993,1,0,0,0,0,1,1,1,1,1,1,1,1],\"FLAG\":0,\"BASE\":1}"
                
            // -- Wi-Fi ---------------------------------------
            #undef WIFI_IP_ADDRESS
                #define WIFI_IP_ADDRESS       "10.99.0.2"         // [IpAddress1] Set to 0.0.0.0 for using DHCP or enter a static IP address
            #undef WIFI_GATEWAY
                #define WIFI_GATEWAY           "10.99.0.1"      // [IpAddress2] If not using DHCP set Gateway IP address
        
            // You might even pass some parameters from the command line ----------------------------
            // Ie:  export PLATFORMIO_BUILD_FLAGS='-DUSE_CONFIG_OVERRIDE -DMY_IP="192.168.1.99" -DMY_GW="192.168.1.1" -DMY_DNS="192.168.1.1"'
        
            #undef STA_SSID1
                #define STA_SSID1              "SERVEUR-DEBITMETRES-PAC-AP"                // [Ssid1] Wi-Fi SSID
            #undef STA_PASS1
                #define STA_PASS1              "Lune5676"                // [Password1] Wi-Fi password
            #undef STA_SSID2
                #define STA_SSID2              ""                // [Ssid2] Optional alternate AP Wi-Fi SSID
            #undef STA_PASS2
                #define STA_PASS2              ""                // [Password2] Optional alternate AP Wi-Fi password
            #undef WIFI_AP_PASSPHRASE
                #define WIFI_AP_PASSPHRASE     ""               // AccessPoint passphrase. For WPA2 min 8 char, for open use "" (max 63 char).
            #undef WIFI_CONFIG_TOOL
                #define WIFI_CONFIG_TOOL       WIFI_WAIT         // [WifiConfig] Default tool if Wi-Fi fails to connect (default option: 4 - WIFI_RETRY)
                                                                    // (0=WIFI_RESTART, 2=WIFI_MANAGER, 4=WIFI_RETRY, 5=WIFI_WAIT, 6=WIFI_SERIAL, 7=WIFI_MANAGER_RESET_ONLY)
        
            // -- Setup your own MQTT settings  ---------------
            #undef MQTT_CLIENT_ID
                #define MQTT_CLIENT_ID "DEBITMETRES-PAC-1" // [MqttClient] Also fall back topic using last 6 characters of MAC address or use "DVES_%12X" for complete MAC address
            #undef MQTT_TOPIC
                #define MQTT_TOPIC "pac/module1" // [Topic] unique MQTT device topic including (part of) device MAC address
            #undef MQTT_GRPTOPIC
                #define MQTT_GRPTOPIC "tasmotas/pac" // [GroupTopic] MQTT Group topic
            #undef FRIENDLY_NAME
                #define FRIENDLY_NAME "Débitmètres PAC 1" // [FriendlyName] Friendlyname up to 32 characters used by webpages and Alexa
            #undef EMULATION
                #define EMULATION EMUL_NONE // [Emulation] Select Belkin WeMo (single relay/light) or Hue Bridge emulation (multi relay/light) (EMUL_NONE, EMUL_WEMO or EMUL_HUE)
            
            // -- Optional modules ----------------------------
            #undef USE_SHUTTER // Add Shutter support for up to 4 shutter with different motortypes (+11k code)
        
            // -- Internal Analog input -----------------------
            #undef USE_ADC_VCC // Display Vcc in Power status. Disable for use as Analog input on selected devices	
        
                // -- Optional light modules ----------------------
            #undef USE_WS2812                               // WS2812 Led string using library NeoPixelBus (+5k code, +1k mem, 232 iram) - Disable by //
                #undef USE_WS2812_HARDWARE  //NEO_HW_WS2812     // Hardware type (NEO_HW_WS2812, NEO_HW_WS2812X, NEO_HW_WS2813, NEO_HW_SK6812, NEO_HW_LC8812, NEO_HW_APA106, NEO_HW_P9813)
                #undef  USE_WS2812_CTYPE     //NEO_GRB           // Color type (NEO_RGB, NEO_GRB, NEO_BRG, NEO_RBG, NEO_RGBW, NEO_GRBW)
            
            // -- LCD I2C -----------------------
            #define USE_I2C             // I2C using library wire (+10k code, 0k2 mem, 124 iram)
            //#define USE_DISPLAY         // Add I2C/TM1637/MAX7219 Display Support (+2k code)
            //#define USE_DISPLAY_SSD1306 // [DisplayModel 2] [I2cDriver4] Enable SSD1306 Oled 128x64 display (I2C addresses 0x3C and 0x3D) (+16k code)
            //#define USE_DISPLAY_SH1106  // [DisplayModel 7] [I2cDriver6] Enable SH1106 Oled 128x64 display (I2C addresses 0x3C and 0x3D)
            //#define USE_GRAPH           // Enable line charts with displays
            //#define NUM_GRAPHS 4        // Max 16
        
            // -- I2C sensors ---------------------------------
            #define I2CDRIVERS_0_31        0xFFFFFFFF        // Enable I2CDriver0  to I2CDriver31
            #define I2CDRIVERS_32_63       0xFFFFFFFF        // Enable I2CDriver32 to I2CDriver63
            #define I2CDRIVERS_64_95       0xFFFFFFFF        // Enable I2CDriver64 to I2CDriver95
            #define I2CDRIVERS_96_127      0xFFFFFFFF        // Enable I2CDriver96 to I2CDriver127
            #define I2CDRIVERS_128_159     0xFFFFFFFF        // Enable I2CDriver128 to I2CDriver159
        
            // -- SPI sensors ---------------------------------
            #define USE_SPI                                  // Hardware SPI using GPIO12(MISO), GPIO13(MOSI) and GPIO14(CLK) in addition to two user selectable GPIOs(CS and DC)
                //#define USE_ILI9488                            // Utilisation de l'ecran ILI9488. Les autres paramètres pour ILI9488 sont gérés par la partie 'Post-process compile options' en fin de fichier
        
            // -- One wire sensors ----------------------------
            #undef USE_HDMI_CEC                              // Add support for HDMI CEC bus (+7k code, 1456 bytes IRAM)
        
            // -- Other sensors/drivers -----------------------
            #define USE_FLOWRATEMETER                        // Add support for water flow meter YF-DN50 and similary (+1k7 code)
            #ifdef USE_FLOWRATEMETER
                //#define D_JSON_FLOWRATEMETER                 "debitmetre" 
            #endif
        
            // GPIO12: 74x595 RClk / GPIO13: 74x595 SRClk / GPIO14: 74x595 Ser
            // Pour utiliser plusieurs 74x595, connecter :
            // - all SRCLK together to GPIO srclk
            // - all RCLK together to GPIO rclk
            // - GPIO ser to SER input of first 74x595
            // - QH' output of first 74x595 to SER input of 2nd 74x595 and so on
            //#define USE_SHIFT595                                // Add support for 74xx595 8-bit shift registers (+0k7 code)
            #ifdef USE_SHIFT595
                #define SHIFT595_INVERT_OUTPUTS false             // [SetOption133] Don't invert outputs of 74x595 shift register
                #define SHIFT595_DEVICE_COUNT  1                  // [Shift595DeviceCount] Set the number of connected 74x595 shift registers
            #endif
        
            // Cf. url: https://templates.blakadder.com/dingtian_DT-R008.html
            //#define USE_DINGTIAN
            #ifdef USE_DINGTIAN
                #define USE_DINGTIAN_RELAY                       // Add support for the Dingian board using 74'595 et 74'165 shift registers
                #define DINGTIAN_INPUTS_INVERTED               // Invert input states (Hi => OFF, Low => ON)
                #define DINGTIAN_USE_AS_BUTTON                 // Inputs as Tasmota's virtual Buttons
                #define DINGTIAN_USE_AS_SWITCH                 // Inputs as Tasmota's virtual Switches
            #endif
        
            // -- Rules or Script  ----------------------------
            // Select none or only one of the below defines USE_RULES or USE_SCRIPT
            #define USE_RULES                                // Add support for rules (+8k code)
            #ifdef USE_RULES
                #define SUPPORT_MQTT_EVENT                     // Support trigger event with MQTT subscriptions (+1k8 code)
                #define USE_EXPRESSION                         // Add support for expression evaluation in rules (+1k7 code)
                    #define SUPPORT_IF_STATEMENT                 // Add support for IF statement in rules (+2k7)
                //#define USER_RULE1 "Rule1 on system#boot do meshbroker endon"          // Add rule1 data saved at initial firmware load or when command reset is executed
                //#define USER_RULE2 "<Any rule2 data>"          // Add rule2 data saved at initial firmware load or when command reset is executed
                //#define USER_RULE3 "<Any rule3 data>"          // Add rule3 data saved at initial firmware load or when command reset is executed
            #endif
            #ifdef USER_BACKLOG
                #undef USER_BACKLOG
            #endif
            #define USER_BACKLOG      "Backlog Module 0; Hostname DEBITMETRES-PAC-1"

        // -- Options for firmware tasmota32-interrupteur-differentiel-bureau ------
        #elif defined(FIRMWARE_ESP32_BUREAU_DISJONCTEUR_DIFFERENTIEL)
            // -- CODE_IMAGE_STR is the name shown between brackets on the 
            //    Information page or in INFO MQTT messages
            #undef CODE_IMAGE_STR
                #define CODE_IMAGE_STR "Disjoncteur Différentiel PC Bureau"
        
            // -- Propriétés des enregistrements des logs dans des fichiers -------------------------------------
            // drivers : tasmota/tasmota_xdrv_driver/xdrv_50_filesystem.ino
            // #define FILE_LOG_SIZE       100
            // #define FILE_LOG_COUNT      10                        // Enable with command `FileLog 1..4` or `FileLog 11..14`
            // #define FILE_LOG_NAME       "/logs/fileLog %02d.txt"
        
            // -- Project -------------------------------------
            #undef PROJECT
                #define PROJECT           "DISJONCTEUR-DIFFERENTIEL-BUREAU"         	 // PROJECT is used as the default topic delimiter
                #define USER_TEMPLATE 		"{\"NAME\":\"Int Diff Nous D3T\",\"GPIO\":[32,1,9312,1,1,320,1,1,9313,8160,3200,544,1,1,1,1,0,1,1,1,0,0,1,1,0,0,0,0,1,1,4736,1,1,0,0,1],\"FLAG\":0,\"BASE\":1}"
                
            // -- Wi-Fi ---------------------------------------
            #undef WIFI_IP_ADDRESS
                #define WIFI_IP_ADDRESS       "192.168.0.49"         // [IpAddress1] Set to 0.0.0.0 for using DHCP or enter a static IP address
        
            // -- Setup your own RANGE EXTENDER settings  -----
            // Les autres paramètres du RangeExtender sont gérés par la partie 'Post-process compile options' en fin de fichier
            // Backlog RgxSSID rangeextender ; RgxPassword securepassword ; RgxAddress 192.168.123.1 ; RgxSubnet 255.255.255.0; RgxState 1 ; RgxNAPT 1
            // RgxPort tcp, 8080, 192.168.4.1, 80
            // #define USE_WIFI_RANGE_EXTENDER
            #ifdef USE_WIFI_RANGE_EXTENDER
                #define WIFI_RGX_SSID           "DISJONCTEUR-DIFFERENTIEL-BUREAU-GATEWAY"
                #define WIFI_RGX_PASSWORD       "Lune5676"
            #endif
        
            // You might even pass some parameters from the command line ----------------------------
            // Ie:  export PLATFORMIO_BUILD_FLAGS='-DUSE_CONFIG_OVERRIDE -DMY_IP="192.168.1.99" -DMY_GW="192.168.1.1" -DMY_DNS="192.168.1.1"'
        
            // -- Setup your own MQTT settings  ---------------
            #undef MQTT_CLIENT_ID
                #define MQTT_CLIENT_ID "DISJONCTEUR-DIFFERENTIEL-BUREAU" // [MqttClient] Also fall back topic using last 6 characters of MAC address or use "DVES_%12X" for complete MAC address
            #undef MQTT_TOPIC
                #define MQTT_TOPIC "bureau/pc" // [Topic] unique MQTT device topic including (part of) device MAC address
            #undef MQTT_GRPTOPIC
                #define MQTT_GRPTOPIC "tasmotas/bureau" // [GroupTopic] MQTT Group topic
            #undef FRIENDLY_NAME
                #define FRIENDLY_NAME "Disjoncteur Différentiel PC Bureau" // [FriendlyName] Friendlyname up to 32 characters used by webpages and Alexa
            #undef EMULATION
                #define EMULATION EMUL_NONE // [Emulation] Select Belkin WeMo (single relay/light) or Hue Bridge emulation (multi relay/light) (EMUL_NONE, EMUL_WEMO or EMUL_HUE)
            
            // -- ESP-NOW -------------------------------------
            // Plus d'info dans le dossier : "Tasmota\info\xdrv_57_tasmesh.md"
            // #define USE_TASMESH                              // Enable Tasmota Mesh using ESP-NOW (+11k code)
        
            // -- Optional modules ----------------------------
            #undef USE_SHUTTER // Add Shutter support for up to 4 shutter with different motortypes (+11k code)
        
            // -- LCD I2C -----------------------
            //#define USE_I2C             // I2C using library wire (+10k code, 0k2 mem, 124 iram)
            //#define USE_DISPLAY         // Add I2C/TM1637/MAX7219 Display Support (+2k code)
            //#define USE_DISPLAY_SSD1306 // [DisplayModel 2] [I2cDriver4] Enable SSD1306 Oled 128x64 display (I2C addresses 0x3C and 0x3D) (+16k code)
            //#define USE_DISPLAY_SH1106  // [DisplayModel 7] [I2cDriver6] Enable SH1106 Oled 128x64 display (I2C addresses 0x3C and 0x3D)
            //#define USE_GRAPH           // Enable line charts with displays
            //#define NUM_GRAPHS 4        // Max 16
        
            // -- I2C sensors ---------------------------------
            #define USE_I2C             // I2C using library wire (+10k code, 0k2 mem, 124 iram)
            #ifdef USE_I2C
                #define I2CDRIVERS_0_31        0xFFFFFFFF        // Enable I2CDriver0  to I2CDriver31
                #define I2CDRIVERS_32_63       0xFFFFFFFF        // Enable I2CDriver32 to I2CDriver63
                #define I2CDRIVERS_64_95       0xFFFFFFFF        // Enable I2CDriver64 to I2CDriver95
                #define I2CDRIVERS_96_127      0xFFFFFFFF        // Enable I2CDriver96 to I2CDriver127
                #define I2CDRIVERS_128_159     0xFFFFFFFF        // Enable I2CDriver128 to I2CDriver159
        
                //#define USE_ADS1115                             // [I2cDriver13] Enable ADS1115 16 bit A/D converter (I2C address 0x48, 0x49, 0x4A or 0x4B) based on Adafruit ADS1x15 library (no library needed) (+0k7 code)
        
                // Cf. url: https://tasmota.github.io/docs/MCP230xx/
                // Vérifier activation du driver : I2cDriver22 1
                // Tester l'adresse du module MCP23XXX (adresse comprise entre 0x20 & 0x26) : I2CScan
                // Les paramètres des I/O est realisé dans le fichier mcp23xx.dat
                // Paramètres Mode 2 MCP23017
                //#define USE_MCP23XXX_DRV
                    //#define USE_MCP230xx_ADDR 0x20                  // Enable MCP23008/MCP23017 I2C Address to use (Must be within range 0x20 through 0x26 - set according to your wired setup)
                    #undef USE_DS1624                                 // [I2cDriver42] Enable DS1624, DS1621 temperature sensor (I2C addresses 0x48 - 0x4F) (+1k2 code)
            #endif
        
            // -- Internal Analog input -----------------------
            //#undef USE_ADC_VCC // Display Vcc in Power status. Disable for use as Analog input on selected devices	
        
            // -- Optional light modules ----------------------
            #define USE_LIGHT                                // Add support for light control
            // #define USE_WS2812                               // WS2812 Led string using library NeoPixelBus (+5k code, +1k mem, 232 iram) - Disable by //
            //  #define USE_WS2812_DMA                         // ESP8266 only, DMA supports only GPIO03 (= Serial RXD) (+1k mem). When USE_WS2812_DMA is enabled expect Exceptions on Pow
                #undef USE_WS2812_RMT
                #define USE_WS2812_RMT  1                      // ESP32 only, hardware RMT support (default). Specify the RMT channel 0..7. This should be preferred to software bit bang.
            //  #define USE_WS2812_I2S  0                      // ESP32 only, hardware I2S support. Specify the I2S channel 0..2. This is exclusive from RMT. By default, prefer RMT support
            //  #define USE_WS2812_INVERTED                    // Use inverted data signal
                #define USE_WS2812_HARDWARE  NEO_HW_WS2812     // Hardware type (NEO_HW_WS2812, NEO_HW_WS2812X, NEO_HW_WS2813, NEO_HW_SK6812, NEO_HW_LC8812, NEO_HW_APA106, NEO_HW_P9813)
                #undef USE_WS2812_CTYPE
                #define USE_WS2812_CTYPE     NEO_GRB           // Color type (NEO_RGB, NEO_GRB, NEO_BRG, NEO_RBG, NEO_RGBW, NEO_GRBW)
        
            // -- One wire sensors ----------------------------
            #undef USE_HDMI_CEC                              // Add support for HDMI CEC bus (+7k code, 1456 bytes IRAM)
            #define USE_DS18x20                              // Add support for DS18x20 sensors with id sort, single scan and read retry (+2k6 code)
            //#define W1_PARASITE_POWER                      // Optimize for parasite powered sensors
            //#define DS18x20_USE_ID_AS_NAME                 // Use last 3 bytes for naming of sensors
            #define DS18x20_USE_ID_ALIAS                      // Add support aliasing for DS18x20 sensors. See comments in xsns_05 files (+0k5 code)
        
            // -- Serial sensors ------------------------------
            // #define USE_MODBUS
            // #define USE_TASMOTA_CLIENT                       // Add support for Arduino Uno/Pro Mini via serial interface including flashing (+2k6 code, 64 mem)
                                                            // GPIO4=Slave TX / GPIO5=Slave RX
        
            // -- Capteurs & Gestion Bluetooth ------------------------------
            // #define USE_BLE_ESP32                              // Add support for ESP32 as a BLE-bridge (+9k2? mem, +292k? flash)
        
            // -- LoRaWan 868MHz ------------------------------
            // #define USE_LORAWAN_BRIDGE      // Add support for LoRaWan bridge (+8k code)
        
            // -- Utilisation des WebSockets ------------------------------
            #define USE_WSSERVER
        
            // -- Rules or Script  ----------------------------
            // Select none or only one of the below defines USE_RULES or USE_SCRIPT
            #define USE_RULES                                                       // Add support for rules (+8k code)
            #ifdef USE_RULES
                #define SUPPORT_MQTT_EVENT                                          // Support trigger event with MQTT subscriptions (+1k8 code)
                #define USE_EXPRESSION                                              // Add support for expression evaluation in rules (+1k7 code)
                    #define SUPPORT_IF_STATEMENT                                    // Add support for IF statement in rules (+2k7)
                //#define USER_RULE1 "ON System#Boot DO Sensor12 S0 ENDON"          // Add rule1 data saved at initial firmware load or when command reset is executed
                //#define USER_RULE2 "<Any rule2 data>"                             // Add rule2 data saved at initial firmware load or when command reset is executed
                //#define USER_RULE3 "<Any rule3 data>"                             // Add rule3 data saved at initial firmware load or when command reset is executed
                #define USE_VIEW_RULE_MEMS_AND_VARS                                 // Enable viewing of rule memories and variables in the web UI (+0k7 code)
            #endif
            #ifdef USER_BACKLOG
                #undef USER_BACKLOG
            #endif
            #define USER_BACKLOG      "Backlog Module 0; Hostname DISJONCTEUR-DIFFERENTIEL-BUREAU"

        // -- Options for firmware tasmota32s3-debitmetres-pac1 ------
        #elif defined(FIRMWARE_ESP32S3_DEBITMETRES_PAC1)
            // -- CODE_IMAGE_STR is the name shown between brackets on the 
            //    Information page or in INFO MQTT messages
            #undef CODE_IMAGE_STR
                #define CODE_IMAGE_STR "debitmetres pac"
        
            // -- Project -------------------------------------
            #undef PROJECT
                #define PROJECT           "DEBITMETRES-PAC"         	 // PROJECT is used as the default topic delimiter
                #define USER_TEMPLATE 		"{\"NAME\":\"ESP32S3 Debitmetres PAC\",\"GPIO\":[1,1,1,1,640,608,1,1,1,1,1,1,1,8993,8992,1,1,1,1,1,1,1,1,1,1,1,1,288,544,1,1,1,1,1,1,1,1,1376],\"FLAG\":0,\"BASE\":1}"
        
            // -- Wi-Fi ---------------------------------------
            #undef WIFI_IP_ADDRESS
                #define WIFI_IP_ADDRESS       "10.99.0.2"         // [IpAddress1] Set to 0.0.0.0 for using DHCP or enter a static IP address
            #undef WIFI_GATEWAY
                #define WIFI_GATEWAY           "10.99.0.1"      // [IpAddress2] If not using DHCP set Gateway IP address
        
            // You might even pass some parameters from the command line ----------------------------
            // Ie:  export PLATFORMIO_BUILD_FLAGS='-DUSE_CONFIG_OVERRIDE -DMY_IP="192.168.1.99" -DMY_GW="192.168.1.1" -DMY_DNS="192.168.1.1"'
        
            #undef STA_SSID1
                #define STA_SSID1              "SERVEUR-DEBITMETRES-PAC-AP"                // [Ssid1] Wi-Fi SSID
            #undef STA_PASS1
                #define STA_PASS1              "Lune5676"                // [Password1] Wi-Fi password
            #undef STA_SSID2
                #define STA_SSID2              ""                // [Ssid2] Optional alternate AP Wi-Fi SSID
            #undef STA_PASS2
                #define STA_PASS2              ""                // [Password2] Optional alternate AP Wi-Fi password
            #undef WIFI_AP_PASSPHRASE
                #define WIFI_AP_PASSPHRASE     ""               // AccessPoint passphrase. For WPA2 min 8 char, for open use "" (max 63 char).
            #undef WIFI_CONFIG_TOOL
                #define WIFI_CONFIG_TOOL       WIFI_WAIT         // [WifiConfig] Default tool if Wi-Fi fails to connect (default option: 4 - WIFI_RETRY)
                                                                    // (0=WIFI_RESTART, 2=WIFI_MANAGER, 4=WIFI_RETRY, 5=WIFI_WAIT, 6=WIFI_SERIAL, 7=WIFI_MANAGER_RESET_ONLY)
        
            // -- Setup your own MQTT settings  ---------------
            #undef MQTT_CLIENT_ID
                #define MQTT_CLIENT_ID "DEBITMETRES-PAC-1" // [MqttClient] Also fall back topic using last 6 characters of MAC address or use "DVES_%12X" for complete MAC address
            #undef MQTT_TOPIC
                #define MQTT_TOPIC "pac/module1" // [Topic] unique MQTT device topic including (part of) device MAC address
            #undef MQTT_GRPTOPIC
                #define MQTT_GRPTOPIC "tasmotas/pac" // [GroupTopic] MQTT Group topic
            #undef FRIENDLY_NAME
                #define FRIENDLY_NAME "Débitmètres PAC 1" // [FriendlyName] Friendlyname up to 32 characters used by webpages and Alexa
            #undef EMULATION
                #define EMULATION EMUL_NONE // [Emulation] Select Belkin WeMo (single relay/light) or Hue Bridge emulation (multi relay/light) (EMUL_NONE, EMUL_WEMO or EMUL_HUE)
            
            // -- Optional modules ----------------------------
            #undef USE_SHUTTER // Add Shutter support for up to 4 shutter with different motortypes (+11k code)
        
            // -- Internal Analog input -----------------------
            #undef USE_ADC_VCC // Display Vcc in Power status. Disable for use as Analog input on selected devices	
        
            // -- Optional light modules ----------------------
            #define USE_LIGHT                                // Add support for light control
            #define USE_WS2812                               // WS2812 Led string using library NeoPixelBus (+5k code, +1k mem, 232 iram) - Disable by //
            //  #define USE_WS2812_DMA                         // ESP8266 only, DMA supports only GPIO03 (= Serial RXD) (+1k mem). When USE_WS2812_DMA is enabled expect Exceptions on Pow
                #define USE_WS2812_RMT  0                      // ESP32 only, hardware RMT support (default). Specify the RMT channel 0..7. This should be preferred to software bit bang.
            //  #define USE_WS2812_I2S  0                      // ESP32 only, hardware I2S support. Specify the I2S channel 0..2. This is exclusive from RMT. By default, prefer RMT support
            //  #define USE_WS2812_INVERTED                    // Use inverted data signal
                #define USE_WS2812_HARDWARE  NEO_HW_WS2812     // Hardware type (NEO_HW_WS2812, NEO_HW_WS2812X, NEO_HW_WS2813, NEO_HW_SK6812, NEO_HW_LC8812, NEO_HW_APA106, NEO_HW_P9813)
                #undef USE_WS2812_CTYPE
                #define USE_WS2812_CTYPE     NEO_GRB           // Color type (NEO_RGB, NEO_GRB, NEO_BRG, NEO_RBG, NEO_RGBW, NEO_GRBW)
            
            #define USE_I2C             // I2C using library wire (+10k code, 0k2 mem, 124 iram)
            #ifdef USE_I2C
                // -- LCD I2C -----------------------
                //#define USE_DISPLAY         // Add I2C/TM1637/MAX7219 Display Support (+2k code)
                //#define USE_DISPLAY_SSD1306 // [DisplayModel 2] [I2cDriver4] Enable SSD1306 Oled 128x64 display (I2C addresses 0x3C and 0x3D) (+16k code)
                //#define USE_DISPLAY_SH1106  // [DisplayModel 7] [I2cDriver6] Enable SH1106 Oled 128x64 display (I2C addresses 0x3C and 0x3D)
                //#define USE_GRAPH           // Enable line charts with displays
                //#define NUM_GRAPHS 4        // Max 16
        
                // -- I2C sensors ---------------------------------
                #define I2CDRIVERS_0_31        0xFFFFFFFF        // Enable I2CDriver0  to I2CDriver31
                #define I2CDRIVERS_32_63       0xFFFFFFFF        // Enable I2CDriver32 to I2CDriver63
                #define I2CDRIVERS_64_95       0xFFFFFFFF        // Enable I2CDriver64 to I2CDriver95
                #define I2CDRIVERS_96_127      0xFFFFFFFF        // Enable I2CDriver96 to I2CDriver127
                #define I2CDRIVERS_128_159     0xFFFFFFFF        // Enable I2CDriver128 to I2CDriver159
        
                // Cf. url: https://tasmota.github.io/docs/MCP230xx/
                // Vérifier activation du driver : I2cDriver22 1
                // Tester l'adresse du module MCP23XXX (adresse comprise entre 0x20 & 0x26) : I2CScan
                // Les paramètres des I/O est realisé dans le fichier mcp23xx.dat
                // Paramètres Mode 2 MCP23017
                #define USE_MCP23XXX_DRV
        
                // Paramètres Mode 1 MCP23017 (mode lancé si echec activation mode 2)
                #ifdef USE_MCP23XXX_DRV
                    #define USE_MCP230xx                            // [I2cDriver22] Enable MCP23008/MCP23017 - Must define I2C Address in #define USE_MCP230xx_ADDR below - range 0x20 - 0x27 (+5k1 code)
                    #define USE_MCP230xx_ADDR 0x20                  // Enable MCP23008/MCP23017 I2C Address to use (Must be within range 0x20 through 0x26 - set according to your wired setup)
                    #define USE_MCP230xx_OUTPUT                     // Enable MCP23008/MCP23017 OUTPUT support through sensor29 commands (+2k2 code)
                    #define USE_MCP230xx_DISPLAYOUTPUT              // Enable MCP23008/MCP23017 to display state of OUTPUT pins on Web UI (+0k2 code)
                #endif
            #endif
        
            // -- SPI sensors ---------------------------------
            #define USE_SPI                                  // Hardware SPI using GPIO12(MISO), GPIO13(MOSI) and GPIO14(CLK) in addition to two user selectable GPIOs(CS and DC)
                //#define USE_ILI9488                            // Utilisation de l'ecran ILI9488. Les autres paramètres pour ILI9488 sont gérés par la partie 'Post-process compile options' en fin de fichier
        
            // -- One wire sensors ----------------------------
            #undef USE_HDMI_CEC                              // Add support for HDMI CEC bus (+7k code, 1456 bytes IRAM)
        
            // -- Other sensors/drivers -----------------------
            #define USE_FLOWRATEMETER                        // Add support for water flow meter YF-DN50 and similary (+1k7 code)
            #ifdef USE_FLOWRATEMETER
                //#define D_JSON_FLOWRATEMETER                 "debitmetre" 
            #endif
        
            // -- Serial sensors ------------------------------
            #define USE_MODBUS
            // #define USE_TASMOTA_CLIENT                       // Add support for Arduino Uno/Pro Mini via serial interface including flashing (+2k6 code, 64 mem)
                                                            // GPIO4=Slave TX / GPIO5=Slave RX
        
            // -- Other sensors/drivers -----------------------
            // GPIO12: 74x595 RClk / GPIO13: 74x595 SRClk / GPIO14: 74x595 Ser
            // Pour utiliser plusieurs 74x595, connecter :
            // - all SRCLK together to GPIO srclk
            // - all RCLK together to GPIO rclk
            // - GPIO ser to SER input of first 74x595
            // - QH' output of first 74x595 to SER input of 2nd 74x595 and so on
            //#define USE_SHIFT595                                // Add support for 74xx595 8-bit shift registers (+0k7 code)
            #ifdef USE_SHIFT595
                #define SHIFT595_INVERT_OUTPUTS false             // [SetOption133] Don't invert outputs of 74x595 shift register
                #define SHIFT595_DEVICE_COUNT  1                  // [Shift595DeviceCount] Set the number of connected 74x595 shift registers
            #endif
        
            // Cf. url: https://templates.blakadder.com/dingtian_DT-R008.html
            //#define USE_DINGTIAN
            #ifdef USE_DINGTIAN
                #define USE_DINGTIAN_RELAY                       // Add support for the Dingian board using 74'595 et 74'165 shift registers
                #define DINGTIAN_INPUTS_INVERTED               // Invert input states (Hi => OFF, Low => ON)
                #define DINGTIAN_USE_AS_BUTTON                 // Inputs as Tasmota's virtual Buttons
                #define DINGTIAN_USE_AS_SWITCH                 // Inputs as Tasmota's virtual Switches
            #endif
        
            // -- Rules or Script  ----------------------------
            // Select none or only one of the below defines USE_RULES or USE_SCRIPT
            #define USE_RULES                                // Add support for rules (+8k code)
            #ifdef USE_RULES
                #define SUPPORT_MQTT_EVENT                      // Support trigger event with MQTT subscriptions (+1k8 code)
                #define USE_EXPRESSION                          // Add support for expression evaluation in rules (+1k7 code)
                    #define SUPPORT_IF_STATEMENT                  // Add support for IF statement in rules (+2k7)
                    #define USER_RULE1 ""                         // Add rule1 data saved at initial firmware load or when command reset is executed
                    #define USER_RULE2 ""                         // Add rule2 data saved at initial firmware load or when command reset is executed
                    #define USER_RULE3 ""                         // Add rule3 data saved at initial firmware load or when command reset is executed
            #endif
            #ifdef USER_BACKLOG
                #undef USER_BACKLOG
            #endif
            #define USER_BACKLOG      "Backlog Module 0; Hostname DEBITMETRES-PAC-1"

        // -- Options for firmware tasmota32s3-maitre-garage-modbus ------
        #elif defined(FIRMWARE_ESP32S3_ETAGE2_GRENIER)
            // -- CODE_IMAGE_STR is the name shown between brackets on the 
            //    Information page or in INFO MQTT messages
            #undef CODE_IMAGE_STR
                #define CODE_IMAGE_STR "Serveur Grenier 2eme"
        
            // -- Propriétés des enregistrements des logs dans des fichiers -------------------------------------
            // drivers : tasmota/tasmota_xdrv_driver/xdrv_50_filesystem.ino
            // #define FILE_LOG_SIZE       100
            // #define FILE_LOG_COUNT      10                        // Enable with command `FileLog 1..4` or `FileLog 11..14`
            // #define FILE_LOG_NAME       "/logs/fileLog %02d.txt"

            // -- Project -------------------------------------
            #undef PROJECT
                #define PROJECT           "SERVEUR-GRENIER-2EME"         	 // PROJECT is used as the default topic delimiter

            #ifdef USER_TEMPLATE
                #undef USER_TEMPLATE
            #endif
            #define USER_TEMPLATE 		"{\"NAME\":\"ESP32S3 Trappe\",\"GPIO\":[1,1,1,1,32,1,1,1,1,1,1,1,1,288,1,1,1,1,1,1,1,1,0,0,0,0,0,544,1,224,225,226,1,1,1,1,1,1],\"FLAG\":0,\"BASE\":1}"

            #ifdef MODULE
                #undef MODULE
            #endif
            #define MODULE USER_MODULE                       // Set template enabled by default
            
            // -- Wi-Fi ---------------------------------------
            #undef WIFI_IP_ADDRESS
                #define WIFI_IP_ADDRESS       "192.168.0.47"         // [IpAddress1] Set to 0.0.0.0 for using DHCP or enter a static IP address

            // -- Setup your own RANGE EXTENDER settings  -----
            // Les autres paramètres du RangeExtender sont gérés par la partie 'Post-process compile options' en fin de fichier
            // Backlog RgxSSID rangeextender ; RgxPassword securepassword ; RgxAddress 192.168.123.1 ; RgxSubnet 255.255.255.0; RgxState 1 ; RgxNAPT 1
            // RgxPort tcp, 8080, 192.168.4.1, 80
            #define USE_WIFI_RANGE_EXTENDER
            #ifdef USE_WIFI_RANGE_EXTENDER
                #define WIFI_RGX_SSID           "SERVEUR-GRENIER-2EME"
                #define WIFI_RGX_PASSWORD       "Lune5676"
            #endif

            // You might even pass some parameters from the command line ----------------------------
            // Ie:  export PLATFORMIO_BUILD_FLAGS='-DUSE_CONFIG_OVERRIDE -DMY_IP="192.168.1.99" -DMY_GW="192.168.1.1" -DMY_DNS="192.168.1.1"'
        
            // -- Setup your own MQTT settings  ---------------
            #undef MQTT_CLIENT_ID
                #define MQTT_CLIENT_ID "SERVEUR-GRENIER-2EME" // [MqttClient] Also fall back topic using last 6 characters of MAC address or use "DVES_%12X" for complete MAC address
            #undef MQTT_TOPIC
                #define MQTT_TOPIC "etage2/grenier" // [Topic] unique MQTT device topic including (part of) device MAC address
            #undef MQTT_GRPTOPIC
                #define MQTT_GRPTOPIC "tasmotas/etage2" // [GroupTopic] MQTT Group topic
            #undef FRIENDLY_NAME
                #define FRIENDLY_NAME "Serveur Grenier 2eme" // [FriendlyName] Friendlyname up to 32 characters used by webpages and Alexa
            #undef EMULATION
                #define EMULATION EMUL_NONE // [Emulation] Select Belkin WeMo (single relay/light) or Hue Bridge emulation (multi relay/light) (EMUL_NONE, EMUL_WEMO or EMUL_HUE)

            // -- ESP-NOW -------------------------------------
            // Plus d'info dans le dossier : "Tasmota\info\xdrv_57_tasmesh.md"
            // #define USE_TASMESH                              // Enable Tasmota Mesh using ESP-NOW (+11k code)
        
            // -- Optional modules ----------------------------
            #define USE_SHUTTER // Add Shutter support for up to 4 shutter with different motortypes (+11k code)
        
            // -- LCD I2C -----------------------
            //#define USE_I2C             // I2C using library wire (+10k code, 0k2 mem, 124 iram)
            //#define USE_DISPLAY         // Add I2C/TM1637/MAX7219 Display Support (+2k code)
            //#define USE_DISPLAY_SSD1306 // [DisplayModel 2] [I2cDriver4] Enable SSD1306 Oled 128x64 display (I2C addresses 0x3C and 0x3D) (+16k code)
            //#define USE_DISPLAY_SH1106  // [DisplayModel 7] [I2cDriver6] Enable SH1106 Oled 128x64 display (I2C addresses 0x3C and 0x3D)
            //#define USE_GRAPH           // Enable line charts with displays
            //#define NUM_GRAPHS 4        // Max 16

            // -- I2C sensors ---------------------------------
            // #define USE_I2C             // I2C using library wire (+10k code, 0k2 mem, 124 iram)
            #ifdef USE_I2C
                #define I2CDRIVERS_0_31        0xFFFFFFFF        // Enable I2CDriver0  to I2CDriver31
                #define I2CDRIVERS_32_63       0xFFFFFFFF        // Enable I2CDriver32 to I2CDriver63
                #define I2CDRIVERS_64_95       0xFFFFFFFF        // Enable I2CDriver64 to I2CDriver95
                #define I2CDRIVERS_96_127      0xFFFFFFFF        // Enable I2CDriver96 to I2CDriver127
                #define I2CDRIVERS_128_159     0xFFFFFFFF        // Enable I2CDriver128 to I2CDriver159
        
                #define USE_ADS1115                             // [I2cDriver13] Enable ADS1115 16 bit A/D converter (I2C address 0x48, 0x49, 0x4A or 0x4B) based on Adafruit ADS1x15 library (no library needed) (+0k7 code)
        
                // Cf. url: https://tasmota.github.io/docs/MCP230xx/
                // Vérifier activation du driver : I2cDriver22 1
                // Tester l'adresse du module MCP23XXX (adresse comprise entre 0x20 & 0x26) : I2CScan
                // Les paramètres des I/O est realisé dans le fichier mcp23xx.dat
                // Paramètres Mode 2 MCP23017
                //#define USE_MCP23XXX_DRV
                    //#define USE_MCP230xx_ADDR 0x20                  // Enable MCP23008/MCP23017 I2C Address to use (Must be within range 0x20 through 0x26 - set according to your wired setup)
                    #undef USE_DS1624                                 // [I2cDriver42] Enable DS1624, DS1621 temperature sensor (I2C addresses 0x48 - 0x4F) (+1k2 code)
            #endif

            // -- Optional light modules ----------------------
            #define USE_LIGHT                                // Add support for light control
            #define USE_WS2812                               // WS2812 Led string using library NeoPixelBus (+5k code, +1k mem, 232 iram) - Disable by //
            //  #define USE_WS2812_DMA                         // ESP8266 only, DMA supports only GPIO03 (= Serial RXD) (+1k mem). When USE_WS2812_DMA is enabled expect Exceptions on Pow
                #undef USE_WS2812_RMT
                #define USE_WS2812_RMT  1                      // ESP32 only, hardware RMT support (default). Specify the RMT channel 0..7. This should be preferred to software bit bang.
            //  #define USE_WS2812_I2S  0                      // ESP32 only, hardware I2S support. Specify the I2S channel 0..2. This is exclusive from RMT. By default, prefer RMT support
            //  #define USE_WS2812_INVERTED                    // Use inverted data signal
                #define USE_WS2812_HARDWARE  NEO_HW_WS2812     // Hardware type (NEO_HW_WS2812, NEO_HW_WS2812X, NEO_HW_WS2813, NEO_HW_SK6812, NEO_HW_LC8812, NEO_HW_APA106, NEO_HW_P9813)
                #undef USE_WS2812_CTYPE
                #define USE_WS2812_CTYPE     NEO_GRB           // Color type (NEO_RGB, NEO_GRB, NEO_BRG, NEO_RBG, NEO_RGBW, NEO_GRBW)

            // -- One wire sensors ----------------------------
            #undef USE_HDMI_CEC                              // Add support for HDMI CEC bus (+7k code, 1456 bytes IRAM)
            // #define USE_DS18x20                              // Add support for DS18x20 sensors with id sort, single scan and read retry (+2k6 code)
                // #define W1_PARASITE_POWER                      // Optimize for parasite powered sensors
                // #define DS18x20_USE_ID_AS_NAME                 // Use last 3 bytes for naming of sensors
                // #define DS18x20_USE_ID_ALIAS                      // Add support aliasing for DS18x20 sensors. See comments in xsns_05 files (+0k5 code)
        
            // -- Serial sensors ------------------------------
            // #define USE_MODBUS
            // #define USE_TASMOTA_CLIENT                       // Add support for Arduino Uno/Pro Mini via serial interface including flashing (+2k6 code, 64 mem)
                                                            // GPIO4=Slave TX / GPIO5=Slave RX
        
            // -- Capteurs & Gestion Bluetooth ------------------------------
            // #define USE_BLE_ESP32                              // Add support for ESP32 as a BLE-bridge (+9k2? mem, +292k? flash)
        
            // -- LoRaWan 868MHz ------------------------------
            // #define USE_LORAWAN_BRIDGE      // Add support for LoRaWan bridge (+8k code)
            // #define USE_LORA_SX126X         // Add driver support for LoRa on SX1262 based devices like LiliGo T3S3 Lora32 (+16k code)

            // -- Rules or Script  ----------------------------
            // Select none or only one of the below defines USE_RULES or USE_SCRIPT
            #define USE_RULES                                                       // Add support for rules (+8k code)
            #ifdef USE_RULES
                #define SUPPORT_MQTT_EVENT                                          // Support trigger event with MQTT subscriptions (+1k8 code)
                #define USE_EXPRESSION                                              // Add support for expression evaluation in rules (+1k7 code)
                    #define SUPPORT_IF_STATEMENT                                    // Add support for IF statement in rules (+2k7)
                //#define USER_RULE1 "ON System#Boot DO Sensor12 S0 ENDON"          // Add rule1 data saved at initial firmware load or when command reset is executed
                //#define USER_RULE2 "<Any rule2 data>"                             // Add rule2 data saved at initial firmware load or when command reset is executed
                //#define USER_RULE3 "<Any rule3 data>"                             // Add rule3 data saved at initial firmware load or when command reset is executed
                #define USE_VIEW_RULE_MEMS_AND_VARS                                 // Enable viewing of rule memories and variables in the web UI (+0k7 code)
            #endif
            #ifdef USER_BACKLOG
                #undef USER_BACKLOG
            #endif
            #define USER_BACKLOG      "Backlog Module 0; Hostname SERVEUR-GRENIER-2EME"
        #elif defined(FIRMWARE_ESP32S3_GARAGE_SERVEUR_MODBUS)
            // -- CODE_IMAGE_STR is the name shown between brackets on the 
            //    Information page or in INFO MQTT messages
            #undef CODE_IMAGE_STR
                #define CODE_IMAGE_STR "Serveur de Garage"
        
            // -- Propriétés des enregistrements des logs dans des fichiers -------------------------------------
            // drivers : tasmota/tasmota_xdrv_driver/xdrv_50_filesystem.ino
            // #define FILE_LOG_SIZE       100
            // #define FILE_LOG_COUNT      10                        // Enable with command `FileLog 1..4` or `FileLog 11..14`
            // #define FILE_LOG_NAME       "/logs/fileLog %02d.txt"
        
            // -- Project -------------------------------------
            #undef PROJECT
                #define PROJECT           "SERVEUR-GARAGE"         	 // PROJECT is used as the default topic delimiter

            #ifdef USER_TEMPLATE
                #undef USER_TEMPLATE
            #endif
            #define USER_TEMPLATE 		"{\"NAME\":\"ESP32S3 Serveur Garage Modbus\",\"GPIO\":[1,1,1,1,9440,9408,1,1,608,640,1,1,1,288,1,1,1,1,1,1,1,1,0,0,0,0,0,544,1,352,1,1,1,1,1,1,1,1],\"FLAG\":0,\"BASE\":1}"

            #ifdef MODULE
                #undef MODULE
            #endif
            #define MODULE USER_MODULE                       // Set template enabled by default
        
            // -- Wi-Fi ---------------------------------------
            #undef WIFI_IP_ADDRESS
                #define WIFI_IP_ADDRESS       "192.168.0.43"         // [IpAddress1] Set to 0.0.0.0 for using DHCP or enter a static IP address
        
            // -- Setup your own RANGE EXTENDER settings  -----
            // Les autres paramètres du RangeExtender sont gérés par la partie 'Post-process compile options' en fin de fichier
            // Backlog RgxSSID rangeextender ; RgxPassword securepassword ; RgxAddress 192.168.123.1 ; RgxSubnet 255.255.255.0; RgxState 1 ; RgxNAPT 1
            // RgxPort tcp, 8080, 192.168.4.1, 80
            #define USE_WIFI_RANGE_EXTENDER
            #ifdef USE_WIFI_RANGE_EXTENDER
                #define WIFI_RGX_SSID           "SERVEUR-GARAGE-GATEWAY"
                #define WIFI_RGX_PASSWORD       "Lune5676"
            #endif
        
            // You might even pass some parameters from the command line ----------------------------
            // Ie:  export PLATFORMIO_BUILD_FLAGS='-DUSE_CONFIG_OVERRIDE -DMY_IP="192.168.1.99" -DMY_GW="192.168.1.1" -DMY_DNS="192.168.1.1"'
        
            // -- Setup your own MQTT settings  ---------------
            #undef MQTT_CLIENT_ID
                #define MQTT_CLIENT_ID "SERVEUR-GARAGE" // [MqttClient] Also fall back topic using last 6 characters of MAC address or use "DVES_%12X" for complete MAC address
            #undef MQTT_TOPIC
                #define MQTT_TOPIC "garage" // [Topic] unique MQTT device topic including (part of) device MAC address
            #undef MQTT_GRPTOPIC
                #define MQTT_GRPTOPIC "tasmotas/garage" // [GroupTopic] MQTT Group topic
            #undef FRIENDLY_NAME
                #define FRIENDLY_NAME "Serveur de Garage" // [FriendlyName] Friendlyname up to 32 characters used by webpages and Alexa
            #undef EMULATION
                #define EMULATION EMUL_NONE // [Emulation] Select Belkin WeMo (single relay/light) or Hue Bridge emulation (multi relay/light) (EMUL_NONE, EMUL_WEMO or EMUL_HUE)
            
            // -- ESP-NOW -------------------------------------
            // Plus d'info dans le dossier : "Tasmota\info\xdrv_57_tasmesh.md"
            // #define USE_TASMESH                              // Enable Tasmota Mesh using ESP-NOW (+11k code)
        
            // -- Optional modules ----------------------------
            #define USE_SHUTTER // Add Shutter support for up to 4 shutter with different motortypes (+11k code)
        
            // -- LCD I2C -----------------------
            //#define USE_I2C             // I2C using library wire (+10k code, 0k2 mem, 124 iram)
            //#define USE_DISPLAY         // Add I2C/TM1637/MAX7219 Display Support (+2k code)
            //#define USE_DISPLAY_SSD1306 // [DisplayModel 2] [I2cDriver4] Enable SSD1306 Oled 128x64 display (I2C addresses 0x3C and 0x3D) (+16k code)
            //#define USE_DISPLAY_SH1106  // [DisplayModel 7] [I2cDriver6] Enable SH1106 Oled 128x64 display (I2C addresses 0x3C and 0x3D)
            //#define USE_GRAPH           // Enable line charts with displays
            //#define NUM_GRAPHS 4        // Max 16
        
            // -- I2C sensors ---------------------------------
            #define USE_I2C             // I2C using library wire (+10k code, 0k2 mem, 124 iram)
            #ifdef USE_I2C
                #define I2CDRIVERS_0_31        0xFFFFFFFF        // Enable I2CDriver0  to I2CDriver31
                #define I2CDRIVERS_32_63       0xFFFFFFFF        // Enable I2CDriver32 to I2CDriver63
                #define I2CDRIVERS_64_95       0xFFFFFFFF        // Enable I2CDriver64 to I2CDriver95
                #define I2CDRIVERS_96_127      0xFFFFFFFF        // Enable I2CDriver96 to I2CDriver127
                #define I2CDRIVERS_128_159     0xFFFFFFFF        // Enable I2CDriver128 to I2CDriver159
        
                #define USE_ADS1115                             // [I2cDriver13] Enable ADS1115 16 bit A/D converter (I2C address 0x48, 0x49, 0x4A or 0x4B) based on Adafruit ADS1x15 library (no library needed) (+0k7 code)
        
                // Cf. url: https://tasmota.github.io/docs/MCP230xx/
                // Vérifier activation du driver : I2cDriver22 1
                // Tester l'adresse du module MCP23XXX (adresse comprise entre 0x20 & 0x26) : I2CScan
                // Les paramètres des I/O est realisé dans le fichier mcp23xx.dat
                // Paramètres Mode 2 MCP23017
                //#define USE_MCP23XXX_DRV
                    //#define USE_MCP230xx_ADDR 0x20                  // Enable MCP23008/MCP23017 I2C Address to use (Must be within range 0x20 through 0x26 - set according to your wired setup)
                    #undef USE_DS1624                                 // [I2cDriver42] Enable DS1624, DS1621 temperature sensor (I2C addresses 0x48 - 0x4F) (+1k2 code)
            #endif
        
            // -- Internal Analog input -----------------------
            //#undef USE_ADC_VCC // Display Vcc in Power status. Disable for use as Analog input on selected devices	
        
            // -- Optional light modules ----------------------
            #define USE_LIGHT                                // Add support for light control
            #define USE_WS2812                               // WS2812 Led string using library NeoPixelBus (+5k code, +1k mem, 232 iram) - Disable by //
            //  #define USE_WS2812_DMA                         // ESP8266 only, DMA supports only GPIO03 (= Serial RXD) (+1k mem). When USE_WS2812_DMA is enabled expect Exceptions on Pow
                #undef USE_WS2812_RMT
                #define USE_WS2812_RMT  1                      // ESP32 only, hardware RMT support (default). Specify the RMT channel 0..7. This should be preferred to software bit bang.
            //  #define USE_WS2812_I2S  0                      // ESP32 only, hardware I2S support. Specify the I2S channel 0..2. This is exclusive from RMT. By default, prefer RMT support
            //  #define USE_WS2812_INVERTED                    // Use inverted data signal
                #define USE_WS2812_HARDWARE  NEO_HW_WS2812     // Hardware type (NEO_HW_WS2812, NEO_HW_WS2812X, NEO_HW_WS2813, NEO_HW_SK6812, NEO_HW_LC8812, NEO_HW_APA106, NEO_HW_P9813)
                #undef USE_WS2812_CTYPE
                #define USE_WS2812_CTYPE     NEO_GRB           // Color type (NEO_RGB, NEO_GRB, NEO_BRG, NEO_RBG, NEO_RGBW, NEO_GRBW)
        
            // -- One wire sensors ----------------------------
            #undef USE_HDMI_CEC                              // Add support for HDMI CEC bus (+7k code, 1456 bytes IRAM)
            #define USE_DS18x20                              // Add support for DS18x20 sensors with id sort, single scan and read retry (+2k6 code)
            //#define W1_PARASITE_POWER                      // Optimize for parasite powered sensors
            //#define DS18x20_USE_ID_AS_NAME                 // Use last 3 bytes for naming of sensors
            #define DS18x20_USE_ID_ALIAS                      // Add support aliasing for DS18x20 sensors. See comments in xsns_05 files (+0k5 code)
        
            // -- Serial sensors ------------------------------
            #define USE_MODBUS
            // #define USE_TASMOTA_CLIENT                       // Add support for Arduino Uno/Pro Mini via serial interface including flashing (+2k6 code, 64 mem)
                                                            // GPIO4=Slave TX / GPIO5=Slave RX
        
            // -- Capteurs & Gestion Bluetooth ------------------------------
            // #define USE_BLE_ESP32                              // Add support for ESP32 as a BLE-bridge (+9k2? mem, +292k? flash)
        
            // -- LoRaWan 868MHz ------------------------------
            #define USE_LORAWAN_BRIDGE      // Add support for LoRaWan bridge (+8k code)
            #define USE_LORA_SX126X         // Add driver support for LoRa on SX1262 based devices like LiliGo T3S3 Lora32 (+16k code)
        
            // -- Utilisation des WebSockets ------------------------------
            #define USE_WSSERVER
        
            // -- Rules or Script  ----------------------------
            // Select none or only one of the below defines USE_RULES or USE_SCRIPT
            #define USE_RULES                                                       // Add support for rules (+8k code)
            #ifdef USE_RULES
                #define SUPPORT_MQTT_EVENT                                          // Support trigger event with MQTT subscriptions (+1k8 code)
                #define USE_EXPRESSION                                              // Add support for expression evaluation in rules (+1k7 code)
                    #define SUPPORT_IF_STATEMENT                                    // Add support for IF statement in rules (+2k7)
                //#define USER_RULE1 "ON System#Boot DO Sensor12 S0 ENDON"          // Add rule1 data saved at initial firmware load or when command reset is executed
                //#define USER_RULE2 "<Any rule2 data>"                             // Add rule2 data saved at initial firmware load or when command reset is executed
                //#define USER_RULE3 "<Any rule3 data>"                             // Add rule3 data saved at initial firmware load or when command reset is executed
                #define USE_VIEW_RULE_MEMS_AND_VARS                                 // Enable viewing of rule memories and variables in the web UI (+0k7 code)
            #endif
            #ifdef USER_BACKLOG
                #undef USER_BACKLOG
            #endif
            #define USER_BACKLOG      "Backlog Hostname SERVEUR-GARAGE"

        // -- Options for tasmota32s3-slave-garage-modbus ------
        #elif defined(FIRMWARE_ESP32S3_CAPTEURS_CUVE_MODBUS)
            // -- CODE_IMAGE_STR is the name shown between brackets on the 
            //    Information page or in INFO MQTT messages
            #undef CODE_IMAGE_STR
                #define CODE_IMAGE_STR "Capteurs de Cuve"
        
            // -- Propriétés des enregistrements des logs dans des fichiers -------------------------------------
            // drivers : tasmota/tasmota_xdrv_driver/xdrv_50_filesystem.ino
            // #define FILE_LOG_SIZE       100
            // #define FILE_LOG_COUNT      10                        // Enable with command `FileLog 1..4` or `FileLog 11..14`
            // #define FILE_LOG_NAME       "/logs/fileLog %02d.txt"
        
            // -- Project -------------------------------------
            #undef PROJECT
                #define PROJECT           "CAPTEURS-CUVE"         	 // PROJECT is used as the default topic delimiter

            #ifdef USER_TEMPLATE
                #undef USER_TEMPLATE
            #endif
            #define USER_TEMPLATE 		"{\"NAME\":\"ESP32S3 Capteur Cuve Modbus\",\"GPIO\":[1,1,1,1,3232,3200,1376,1,608,640,1,1,1,1,1,1,1,1,1312,1,1,1,0,0,0,0,0,544,288,1,1,1,1,1,1,1,1,1],\"FLAG\":0,\"BASE\":1}"

            #ifdef MODULE
                #undef MODULE
            #endif
            #define MODULE USER_MODULE                       // Set template enabled by default
        
            // -- Wi-Fi ---------------------------------------
            #undef WIFI_IP_ADDRESS
                #define WIFI_IP_ADDRESS        "0.0.0.0"         // [IpAddress1] Set to 0.0.0.0 for using DHCP or enter a static IP address
            #undef WIFI_GATEWAY
                #define WIFI_GATEWAY           "192.168.4.1"      // [IpAddress2] If not using DHCP set Gateway IP address
            #undef WIFI_DNS
                #define WIFI_DNS               "192.168.0.254"      // [IpAddress4] If not using DHCP set DNS1 IP address (might be equal to WIFI_GATEWAY)
        
            #undef STA_SSID1
                #define STA_SSID1              "SERVEUR-GARAGE-GATEWAY"                // [Ssid1] Wi-Fi SSID
            #undef STA_PASS1
                #define STA_PASS1              "Lune5676"                // [Password1] Wi-Fi password
            #undef STA_SSID2
                #define STA_SSID2              "iPhone de Frederic"                // [Ssid2] Optional alternate AP Wi-Fi SSID
            #undef STA_PASS2
                #define STA_PASS2              "Lune5676"                // [Password2] Optional alternate AP Wi-Fi password
        
            #undef WIFI_CONFIG_TOOL
                #define WIFI_CONFIG_TOOL       WIFI_WAIT        // [WifiConfig] Default tool if Wi-Fi fails to connect (default option: 4 - WIFI_RETRY)
                                                                // (WIFI_RESTART, WIFI_MANAGER, WIFI_RETRY, WIFI_WAIT, WIFI_SERIAL, WIFI_MANAGER_RESET_ONLY)
                                                                // The configuration can be changed after first setup using WifiConfig 0, 2, 4, 5, 6 and 7.
        
            // -- Setup your own RANGE EXTENDER settings  -----
            // Les autres paramètres du RangeExtender sont gérés par la partie 'Post-process compile options' en fin de fichier
            // Backlog RgxSSID rangeextender ; RgxPassword securepassword ; RgxAddress 192.168.123.1 ; RgxSubnet 255.255.255.0; RgxState 1 ; RgxNAPT 1
            // RgxPort tcp, 8080, 192.168.4.1, 80
            #define USE_WIFI_RANGE_EXTENDER
            #ifdef USE_WIFI_RANGE_EXTENDER
                #define WIFI_RGX_SSID           "CAPTEURS-CUVE-GATEWAY"
                #define WIFI_RGX_PASSWORD       "Lune5676"
            #endif
        
            // You might even pass some parameters from the command line ----------------------------
            // Ie:  export PLATFORMIO_BUILD_FLAGS='-DUSE_CONFIG_OVERRIDE -DMY_IP="192.168.1.99" -DMY_GW="192.168.1.1" -DMY_DNS="192.168.1.1"'
        
            // -- Setup your own MQTT settings  ---------------
            #undef MQTT_CLIENT_ID
                #define MQTT_CLIENT_ID "CAPTEURS-CUVE" // [MqttClient] Also fall back topic using last 6 characters of MAC address or use "DVES_%12X" for complete MAC address
            #undef MQTT_TOPIC
                #define MQTT_TOPIC "jardin/cuve" // [Topic] unique MQTT device topic including (part of) device MAC address
            #undef MQTT_GRPTOPIC
                #define MQTT_GRPTOPIC "tasmotas/garage" // [GroupTopic] MQTT Group topic
            #undef FRIENDLY_NAME
                #define FRIENDLY_NAME "Capteurs de Cuve" // [FriendlyName] Friendlyname up to 32 characters used by webpages and Alexa
            #undef EMULATION
                #define EMULATION EMUL_NONE // [Emulation] Select Belkin WeMo (single relay/light) or Hue Bridge emulation (multi relay/light) (EMUL_NONE, EMUL_WEMO or EMUL_HUE)
        
            // -- ESP-NOW -------------------------------------
            // Plus d'info dans le dossier : "Tasmota\info\xdrv_57_tasmesh.md"
            // #define USE_TASMESH                              // Enable Tasmota Mesh using ESP-NOW (+11k code)
        
            // -- Optional modules ----------------------------
            #undef USE_SHUTTER // Add Shutter support for up to 4 shutter with different motortypes (+11k code)
        
            // -- LCD I2C -----------------------
            //#define USE_I2C             // I2C using library wire (+10k code, 0k2 mem, 124 iram)
            //#define USE_DISPLAY         // Add I2C/TM1637/MAX7219 Display Support (+2k code)
            //#define USE_DISPLAY_SSD1306 // [DisplayModel 2] [I2cDriver4] Enable SSD1306 Oled 128x64 display (I2C addresses 0x3C and 0x3D) (+16k code)
            //#define USE_DISPLAY_SH1106  // [DisplayModel 7] [I2cDriver6] Enable SH1106 Oled 128x64 display (I2C addresses 0x3C and 0x3D)
            //#define USE_GRAPH           // Enable line charts with displays
            //#define NUM_GRAPHS 4        // Max 16
        
            // -- I2C sensors ---------------------------------
            #define USE_I2C             // I2C using library wire (+10k code, 0k2 mem, 124 iram)
            #ifdef USE_I2C
                #define I2CDRIVERS_0_31        0xFFFFFFFF        // Enable I2CDriver0  to I2CDriver31
                #define I2CDRIVERS_32_63       0xFFFFFFFF        // Enable I2CDriver32 to I2CDriver63
                #define I2CDRIVERS_64_95       0xFFFFFFFF        // Enable I2CDriver64 to I2CDriver95
                #define I2CDRIVERS_96_127      0xFFFFFFFF        // Enable I2CDriver96 to I2CDriver127
                #define I2CDRIVERS_128_159     0xFFFFFFFF        // Enable I2CDriver128 to I2CDriver159
        
                #define USE_ADS1115                             // [I2cDriver13] Enable ADS1115 16 bit A/D converter (I2C address 0x48, 0x49, 0x4A or 0x4B) based on Adafruit ADS1x15 library (no library needed) (+0k7 code)
        
                // Cf. url: https://tasmota.github.io/docs/MCP230xx/
                // Vérifier activation du driver : I2cDriver22 1
                // Tester l'adresse du module MCP23XXX (adresse comprise entre 0x20 & 0x26) : I2CScan
                // Les paramètres des I/O est realisé dans le fichier mcp23xx.dat
                // Paramètres Mode 2 MCP23017
                //#define USE_MCP23XXX_DRV
                    //#define USE_MCP230xx_ADDR 0x20                  // Enable MCP23008/MCP23017 I2C Address to use (Must be within range 0x20 through 0x26 - set according to your wired setup)
                    #undef USE_DS1624                                 // [I2cDriver42] Enable DS1624, DS1621 temperature sensor (I2C addresses 0x48 - 0x4F) (+1k2 code)
        
                // #define USE_RTC_CHIPS                                 // Enable RTC chip support and NTP server
            #endif
        
            // -- Internal Analog input -----------------------
            //#undef USE_ADC_VCC // Display Vcc in Power status. Disable for use as Analog input on selected devices	
        
            // -- Optional light modules ----------------------
            #define USE_LIGHT                                // Add support for light control
            #define USE_WS2812                               // WS2812 Led string using library NeoPixelBus (+5k code, +1k mem, 232 iram) - Disable by //
            //  #define USE_WS2812_DMA                         // ESP8266 only, DMA supports only GPIO03 (= Serial RXD) (+1k mem). When USE_WS2812_DMA is enabled expect Exceptions on Pow
                #define USE_WS2812_RMT  0                      // ESP32 only, hardware RMT support (default). Specify the RMT channel 0..7. This should be preferred to software bit bang.
            //  #define USE_WS2812_I2S  0                      // ESP32 only, hardware I2S support. Specify the I2S channel 0..2. This is exclusive from RMT. By default, prefer RMT support
            //  #define USE_WS2812_INVERTED                    // Use inverted data signal
                #define USE_WS2812_HARDWARE  NEO_HW_WS2812     // Hardware type (NEO_HW_WS2812, NEO_HW_WS2812X, NEO_HW_WS2813, NEO_HW_SK6812, NEO_HW_LC8812, NEO_HW_APA106, NEO_HW_P9813)
                #undef USE_WS2812_CTYPE
                #define USE_WS2812_CTYPE     NEO_GRB           // Color type (NEO_RGB, NEO_GRB, NEO_BRG, NEO_RBG, NEO_RGBW, NEO_GRBW)
        
            // -- One wire sensors ----------------------------
            #undef USE_HDMI_CEC                              // Add support for HDMI CEC bus (+7k code, 1456 bytes IRAM)
            #define USE_DS18x20                              // Add support for DS18x20 sensors with id sort, single scan and read retry (+2k6 code)
            //#define W1_PARASITE_POWER                      // Optimize for parasite powered sensors
            //#define DS18x20_USE_ID_AS_NAME                 // Use last 3 bytes for naming of sensors
            #define DS18x20_USE_ID_ALIAS                      // Add support aliasing for DS18x20 sensors. See comments in xsns_05 files (+0k5 code)
        
            // -- One wire sensors ----------------------------
            #undef USE_HDMI_CEC                              // Add support for HDMI CEC bus (+7k code, 1456 bytes IRAM)
        
            // -- Serial sensors ------------------------------
            #define USE_MODBUS
            // #define USE_TASMOTA_CLIENT                       // Add support for Arduino Uno/Pro Mini via serial interface including flashing (+2k6 code, 64 mem)
                                                            // GPIO4=Slave TX / GPIO5=Slave RX
        
            // -- LoRaWan 868MHz ------------------------------
            #define USE_LORAWAN_BRIDGE      // Add support for LoRaWan bridge (+8k code)
            #define USE_LORA_SX126X         // Add driver support for LoRa on SX1262 based devices like LiliGo T3S3 Lora32 (+16k code)
            
            // -- Utilisation des WebSockets ------------------------------
            #define USE_WSSERVER
        
            // -- Rules or Script  ----------------------------
            // Select none or only one of the below defines USE_RULES or USE_SCRIPT
            #define USE_RULES                                                       // Add support for rules (+8k code)
            #ifdef USE_RULES
                #define SUPPORT_MQTT_EVENT                                          // Support trigger event with MQTT subscriptions (+1k8 code)
                #define USE_EXPRESSION                                              // Add support for expression evaluation in rules (+1k7 code)
                    #define SUPPORT_IF_STATEMENT                                    // Add support for IF statement in rules (+2k7)
                //#define USER_RULE1 "<Any rule1 data>"                             // Add rule1 data saved at initial firmware load or when command reset is executed
                //#define USER_RULE2 "<Any rule2 data>"                             // Add rule2 data saved at initial firmware load or when command reset is executed
                //#define USER_RULE3 "<Any rule3 data>"                             // Add rule3 data saved at initial firmware load or when command reset is executed
                #define USE_VIEW_RULE_MEMS_AND_VARS                                 // Enable viewing of rule memories and variables in the web UI (+0k7 code)
            #endif
            #ifdef USER_BACKLOG
                #undef USER_BACKLOG
            #endif
            #define USER_BACKLOG      "Backlog Hostname CAPTEURS-CUVE"

        // -- Options for tasmota32-rideau-garage-modbus ------
        #elif defined(FIRMWARE_ESP32S3_RIDEAU_GARAGE_MODBUS)
            // -- CODE_IMAGE_STR is the name shown between brackets on the 
            //    Information page or in INFO MQTT messages
            #undef CODE_IMAGE_STR
                #define CODE_IMAGE_STR "Rideau de garage"
        
            // -- Propriétés des enregistrements des logs dans des fichiers -------------------------------------
            // drivers : tasmota/tasmota_xdrv_driver/xdrv_50_filesystem.ino
            // #define FILE_LOG_SIZE       100
            // #define FILE_LOG_COUNT      10                        // Enable with command `FileLog 1..4` or `FileLog 11..14`
            // #define FILE_LOG_NAME       "/logs/fileLog %02d.txt"
        
            // -- Project -------------------------------------
            #undef PROJECT
                #define PROJECT           "RIDEAU-GARAGE"         	 // PROJECT is used as the default topic delimiter

            #ifdef USER_TEMPLATE
                #undef USER_TEMPLATE
            #endif
            #define USER_TEMPLATE 		"{\"NAME\":\"ESP32S3 Rideau Garage Modbus\",\"GPIO\":[1,1,1,1,3232,3200,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,544,288,1,224,225,1,1,1,1,1,1s],\"FLAG\":0,\"BASE\":1}"

            #ifdef MODULE
                #undef MODULE
            #endif
            #define MODULE USER_MODULE                       // Set template enabled by default
        
            // -- Wi-Fi ---------------------------------------
            #undef WIFI_IP_ADDRESS
                #define WIFI_IP_ADDRESS        "0.0.0.0"         // [IpAddress1] Set to 0.0.0.0 for using DHCP or enter a static IP address
            #undef WIFI_GATEWAY
                #define WIFI_GATEWAY           "192.168.4.1"      // [IpAddress2] If not using DHCP set Gateway IP address
            #undef WIFI_DNS
                #define WIFI_DNS               "192.168.0.254"      // [IpAddress4] If not using DHCP set DNS1 IP address (might be equal to WIFI_GATEWAY)
        
            #undef STA_SSID1
                #define STA_SSID1              "SERVEUR-GARAGE-GATEWAY"                // [Ssid1] Wi-Fi SSID
            #undef STA_PASS1
                #define STA_PASS1              "Lune5676"                // [Password1] Wi-Fi password
            #undef STA_SSID2
                #define STA_SSID2              "iPhone de Frederic"                // [Ssid2] Optional alternate AP Wi-Fi SSID
            #undef STA_PASS2
                #define STA_PASS2              "Lune5676"                // [Password2] Optional alternate AP Wi-Fi password
        
            #undef WIFI_CONFIG_TOOL
                #define WIFI_CONFIG_TOOL       WIFI_WAIT        // [WifiConfig] Default tool if Wi-Fi fails to connect (default option: 4 - WIFI_RETRY)
                                                                // (WIFI_RESTART, WIFI_MANAGER, WIFI_RETRY, WIFI_WAIT, WIFI_SERIAL, WIFI_MANAGER_RESET_ONLY)
                                                                // The configuration can be changed after first setup using WifiConfig 0, 2, 4, 5, 6 and 7.
        
            // -- Setup your own RANGE EXTENDER settings  -----
            // Les autres paramètres du RangeExtender sont gérés par la partie 'Post-process compile options' en fin de fichier
            // Backlog RgxSSID rangeextender ; RgxPassword securepassword ; RgxAddress 192.168.123.1 ; RgxSubnet 255.255.255.0; RgxState 1 ; RgxNAPT 1
            // RgxPort tcp, 8080, 192.168.4.1, 80
            #define USE_WIFI_RANGE_EXTENDER
            #ifdef USE_WIFI_RANGE_EXTENDER
                #define WIFI_RGX_SSID           "RIDEAU-GARAGE-GATEWAY"
                #define WIFI_RGX_PASSWORD       "Lune5676"
            #endif
        
            // You might even pass some parameters from the command line ----------------------------
            // Ie:  export PLATFORMIO_BUILD_FLAGS='-DUSE_CONFIG_OVERRIDE -DMY_IP="192.168.1.99" -DMY_GW="192.168.1.1" -DMY_DNS="192.168.1.1"'
        
            // -- Setup your own MQTT settings  ---------------
            #undef MQTT_CLIENT_ID
                #define MQTT_CLIENT_ID "RIDEAU-GARAGE" // [MqttClient] Also fall back topic using last 6 characters of MAC address or use "DVES_%12X" for complete MAC address
            #undef MQTT_TOPIC
                #define MQTT_TOPIC "garage/rideau" // [Topic] unique MQTT device topic including (part of) device MAC address
            #undef MQTT_GRPTOPIC
                #define MQTT_GRPTOPIC "tasmotas/garage" // [GroupTopic] MQTT Group topic
            #undef FRIENDLY_NAME
                #define FRIENDLY_NAME "Rideau de Garage" // [FriendlyName] Friendlyname up to 32 characters used by webpages and Alexa
            #undef EMULATION
                #define EMULATION EMUL_NONE // [Emulation] Select Belkin WeMo (single relay/light) or Hue Bridge emulation (multi relay/light) (EMUL_NONE, EMUL_WEMO or EMUL_HUE)
        
            // -- ESP-NOW -------------------------------------
            // Plus d'info dans le dossier : "Tasmota\info\xdrv_57_tasmesh.md"
            //#define USE_TASMESH                              // Enable Tasmota Mesh using ESP-NOW (+11k code)
        
            // -- Optional modules ----------------------------
            #define USE_SHUTTER // Add Shutter support for up to 4 shutter with different motortypes (+11k code)
        
            // -- LCD I2C -----------------------
            //#define USE_I2C             // I2C using library wire (+10k code, 0k2 mem, 124 iram)
            //#define USE_DISPLAY         // Add I2C/TM1637/MAX7219 Display Support (+2k code)
            //#define USE_DISPLAY_SSD1306 // [DisplayModel 2] [I2cDriver4] Enable SSD1306 Oled 128x64 display (I2C addresses 0x3C and 0x3D) (+16k code)
            //#define USE_DISPLAY_SH1106  // [DisplayModel 7] [I2cDriver6] Enable SH1106 Oled 128x64 display (I2C addresses 0x3C and 0x3D)
            //#define USE_GRAPH           // Enable line charts with displays
            //#define NUM_GRAPHS 4        // Max 16
        
            // -- I2C sensors ---------------------------------
            #define USE_I2C             // I2C using library wire (+10k code, 0k2 mem, 124 iram)
            #ifdef USE_I2C
                #define I2CDRIVERS_0_31        0xFFFFFFFF        // Enable I2CDriver0  to I2CDriver31
                #define I2CDRIVERS_32_63       0xFFFFFFFF        // Enable I2CDriver32 to I2CDriver63
                #define I2CDRIVERS_64_95       0xFFFFFFFF        // Enable I2CDriver64 to I2CDriver95
                #define I2CDRIVERS_96_127      0xFFFFFFFF        // Enable I2CDriver96 to I2CDriver127
                #define I2CDRIVERS_128_159     0xFFFFFFFF        // Enable I2CDriver128 to I2CDriver159
        
                // #define USE_ADS1115                             // [I2cDriver13] Enable ADS1115 16 bit A/D converter (I2C address 0x48, 0x49, 0x4A or 0x4B) based on Adafruit ADS1x15 library (no library needed) (+0k7 code)
        
                // Cf. url: https://tasmota.github.io/docs/MCP230xx/
                // Vérifier activation du driver : I2cDriver22 1
                // Tester l'adresse du module MCP23XXX (adresse comprise entre 0x20 & 0x26) : I2CScan
                // Les paramètres des I/O est realisé dans le fichier mcp23xx.dat
                // Paramètres Mode 2 MCP23017
                //#define USE_MCP23XXX_DRV
                    //#define USE_MCP230xx_ADDR 0x20                  // Enable MCP23008/MCP23017 I2C Address to use (Must be within range 0x20 through 0x26 - set according to your wired setup)
                    #undef USE_DS1624                                 // [I2cDriver42] Enable DS1624, DS1621 temperature sensor (I2C addresses 0x48 - 0x4F) (+1k2 code)
        
                // #define USE_RTC_CHIPS                                 // Enable RTC chip support and NTP server
            #endif
        
            // -- Internal Analog input -----------------------
            //#undef USE_ADC_VCC // Display Vcc in Power status. Disable for use as Analog input on selected devices	
        
            // -- Optional light modules ----------------------
            #define USE_LIGHT                                // Add support for light control
            #define USE_WS2812                               // WS2812 Led string using library NeoPixelBus (+5k code, +1k mem, 232 iram) - Disable by //
            //  #define USE_WS2812_DMA                         // ESP8266 only, DMA supports only GPIO03 (= Serial RXD) (+1k mem). When USE_WS2812_DMA is enabled expect Exceptions on Pow
                #define USE_WS2812_RMT  0                      // ESP32 only, hardware RMT support (default). Specify the RMT channel 0..7. This should be preferred to software bit bang.
            //  #define USE_WS2812_I2S  0                      // ESP32 only, hardware I2S support. Specify the I2S channel 0..2. This is exclusive from RMT. By default, prefer RMT support
            //  #define USE_WS2812_INVERTED                    // Use inverted data signal
                #define USE_WS2812_HARDWARE  NEO_HW_WS2812     // Hardware type (NEO_HW_WS2812, NEO_HW_WS2812X, NEO_HW_WS2813, NEO_HW_SK6812, NEO_HW_LC8812, NEO_HW_APA106, NEO_HW_P9813)
                #undef USE_WS2812_CTYPE
                #define USE_WS2812_CTYPE     NEO_GRB           // Color type (NEO_RGB, NEO_GRB, NEO_BRG, NEO_RBG, NEO_RGBW, NEO_GRBW)
        
            // -- One wire sensors ----------------------------
            #undef USE_HDMI_CEC                              // Add support for HDMI CEC bus (+7k code, 1456 bytes IRAM)
            #define USE_DS18x20                              // Add support for DS18x20 sensors with id sort, single scan and read retry (+2k6 code)
            //#define W1_PARASITE_POWER                      // Optimize for parasite powered sensors
            //#define DS18x20_USE_ID_AS_NAME                 // Use last 3 bytes for naming of sensors
            // #define DS18x20_USE_ID_ALIAS                      // Add support aliasing for DS18x20 sensors. See comments in xsns_05 files (+0k5 code)
        
            // -- One wire sensors ----------------------------
            #undef USE_HDMI_CEC                              // Add support for HDMI CEC bus (+7k code, 1456 bytes IRAM)
        
            // -- Serial sensors ------------------------------
            #define USE_MODBUS
            // #define USE_TASMOTA_CLIENT                       // Add support for Arduino Uno/Pro Mini via serial interface including flashing (+2k6 code, 64 mem)
                                                            // GPIO4=Slave TX / GPIO5=Slave RX
        
            // -- LoRaWan 868MHz ------------------------------
            #define USE_LORAWAN_BRIDGE      // Add support for LoRaWan bridge (+8k code)
            #define USE_LORA_SX126X         // Add driver support for LoRa on SX1262 based devices like LiliGo T3S3 Lora32 (+16k code)
            
            // -- Utilisation des WebSockets ------------------------------
            #define USE_WSSERVER
        
            // -- Rules or Script  ----------------------------
            // Select none or only one of the below defines USE_RULES or USE_SCRIPT
            #define USE_RULES                                                       // Add support for rules (+8k code)
            #ifdef USE_RULES
                #define SUPPORT_MQTT_EVENT                                          // Support trigger event with MQTT subscriptions (+1k8 code)
                #define USE_EXPRESSION                                              // Add support for expression evaluation in rules (+1k7 code)
                    #define SUPPORT_IF_STATEMENT                                    // Add support for IF statement in rules (+2k7)
                //#define USER_RULE1 "<Any rule1 data>"                             // Add rule1 data saved at initial firmware load or when command reset is executed
                //#define USER_RULE2 "<Any rule2 data>"                             // Add rule2 data saved at initial firmware load or when command reset is executed
                //#define USER_RULE3 "<Any rule3 data>"                             // Add rule3 data saved at initial firmware load or when command reset is executed
                #define USE_VIEW_RULE_MEMS_AND_VARS                                 // Enable viewing of rule memories and variables in the web UI (+0k7 code)
            #endif
            #ifdef USER_BACKLOG
                #undef USER_BACKLOG
            #endif
            #define USER_BACKLOG      "Backlog Hostname RIDEAU-GARAGE"

        // -- Options for tasmota32p4-wifi6 ------
        #elif defined(FIRMWARE_ESP32P4_GARAGE_SERVEUR_MODBUS)
            // -- CODE_IMAGE_STR is the name shown between brackets on the 
            //    Information page or in INFO MQTT messages
            #ifdef CODE_IMAGE_STR
                #undef CODE_IMAGE_STR
            #endif
            #define CODE_IMAGE_STR      "Serveur de Garage"
        
            // -- Propriétés des enregistrements des logs dans des fichiers -------------------------------------
            // drivers : tasmota/tasmota_xdrv_driver/xdrv_50_filesystem.ino
            // #define FILE_LOG_SIZE       100
            // #define FILE_LOG_COUNT      10                        // Enable with command `FileLog 1..4` or `FileLog 11..14`
            // #define FILE_LOG_NAME       "/logs/fileLog %02d.txt"

            // -- Project -------------------------------------
            #ifdef PROJECT
                #undef PROJECT
            #endif
            #define PROJECT             "SERVEUR-GARAGE"         	 // PROJECT is used as the default topic delimiter
            #ifdef USER_TEMPLATE
                #undef USER_TEMPLATE
            #endif

            #if defined(ESP32P4_BASE_DEVKIT)
                #define USER_TEMPLATE 		"{\"NAME\":\"ESP32P4 Serveur Garage Modbus\",\"GPIO\":[1,1,1,1,9440,9408,1,640,608,7776,7840,7872,7808,9376,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,5568,1,1,1,1,1,1,1,8864,8896,8928,8960,8832,8800,6720,1,1,1,1,1,5536,5600,1,1],\"FLAG\":0,\"BASE\":1,\"CMND\":\"ethtype 1|ethaddress -1\"}"
            #elif defined(ESP32P4_BASE_WIFI6)
                #define USER_TEMPLATE 		"{\"NAME\":\"ESP32P4 Serveur Garage Modbus\",\"GPIO\":[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],\"FLAG\":0,\"BASE\":1}"
            #endif
            // #define USER_TEMPLATE 		"{\"NAME\":\"ESP32P4 Serveur Garage Modbus\",\"GPIO\":[1,1,1,1,9440,9408,1,1,608,640,1,1,1,1,8864,8896,8928,8960,8832,8800,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,352,1,1,1,1,1,1,1,1,1,1,1,1,1,8736],\"FLAG\":0,\"BASE\":1}"

            #ifdef MODULE
                #undef MODULE
            #endif
            #define MODULE USER_MODULE                       // Set template enabled by default

            // -- Wi-Fi ---------------------------------------
            #ifdef WIFI_IP_ADDRESS
                #undef WIFI_IP_ADDRESS
            #endif
            #define WIFI_IP_ADDRESS         "192.168.0.43"               // [IpAddress1] Set to 0.0.0.0 for using DHCP or enter a static IP address

            // -- Setup your own RANGE EXTENDER settings  -----
            // Les autres paramètres du RangeExtender sont gérés par la partie 'Post-process compile options' en fin de fichier
            // Backlog RgxSSID rangeextender ; RgxPassword securepassword ; RgxAddress 192.168.123.1 ; RgxSubnet 255.255.255.0; RgxState 1 ; RgxNAPT 1
            // RgxPort tcp, 8080, 192.168.4.1, 80
            #define USE_WIFI_RANGE_EXTENDER
            #ifdef USE_WIFI_RANGE_EXTENDER
                #define WIFI_RGX_SSID           "SERVEUR-GARAGE-GATEWAY"
                #define WIFI_RGX_PASSWORD       "Lune5676"
            #endif

            // You might even pass some parameters from the command line ----------------------------
            // Ie:  export PLATFORMIO_BUILD_FLAGS='-DUSE_CONFIG_OVERRIDE -DMY_IP="192.168.1.99" -DMY_GW="192.168.1.1" -DMY_DNS="192.168.1.1"'
        
            // -- Setup your own MQTT settings  ---------------
            #ifdef MQTT_CLIENT_ID
                #undef MQTT_CLIENT_ID
            #endif
            #define MQTT_CLIENT_ID          "SERVEUR-GARAGE" // [MqttClient] Also fall back topic using last 6 characters of MAC address or use "DVES_%12X" for complete MAC address
            #ifdef MQTT_TOPIC
                #undef MQTT_TOPIC
            #endif
            #define MQTT_TOPIC              "garage" // [Topic] unique MQTT device topic including (part of) device MAC address
            #ifdef MQTT_GRPTOPIC
                #undef MQTT_GRPTOPIC
            #endif
                #define MQTT_GRPTOPIC       "tasmotas/garage" // [GroupTopic] MQTT Group topic
            #ifdef FRIENDLY_NAME
                #undef FRIENDLY_NAME
            #endif
            #define FRIENDLY_NAME           "Serveur de Garage" // [FriendlyName] Friendlyname up to 32 characters used by webpages and Alexa
            #ifdef EMULATION
                #undef EMULATION
            #endif
            #define EMULATION               EMUL_NONE // [Emulation] Select Belkin WeMo (single relay/light) or Hue Bridge emulation (multi relay/light) (EMUL_NONE, EMUL_WEMO or EMUL_HUE)

            // -- ESP-NOW -------------------------------------
            // Plus d'info dans le dossier : "Tasmota\info\xdrv_57_tasmesh.md"
            // #define USE_TASMESH                              // Enable Tasmota Mesh using ESP-NOW (+11k code)
        
            // -- Optional modules ----------------------------
            #define USE_SHUTTER // Add Shutter support for up to 4 shutter with different motortypes (+11k code)

            // -- LCD I2C -----------------------
            //#define USE_I2C             // I2C using library wire (+10k code, 0k2 mem, 124 iram)
            //#define USE_DISPLAY         // Add I2C/TM1637/MAX7219 Display Support (+2k code)
            //#define USE_DISPLAY_SSD1306 // [DisplayModel 2] [I2cDriver4] Enable SSD1306 Oled 128x64 display (I2C addresses 0x3C and 0x3D) (+16k code)
            //#define USE_DISPLAY_SH1106  // [DisplayModel 7] [I2cDriver6] Enable SH1106 Oled 128x64 display (I2C addresses 0x3C and 0x3D)
            //#define USE_GRAPH           // Enable line charts with displays
            //#define NUM_GRAPHS 4        // Max 16
        
            // -- I2C sensors ---------------------------------
            #define USE_I2C             // I2C using library wire (+10k code, 0k2 mem, 124 iram)
            #ifdef USE_I2C
                #define I2CDRIVERS_0_31        0xFFFFFFFF        // Enable I2CDriver0  to I2CDriver31
                #define I2CDRIVERS_32_63       0xFFFFFFFF        // Enable I2CDriver32 to I2CDriver63
                #define I2CDRIVERS_64_95       0xFFFFFFFF        // Enable I2CDriver64 to I2CDriver95
                #define I2CDRIVERS_96_127      0xFFFFFFFF        // Enable I2CDriver96 to I2CDriver127
                #define I2CDRIVERS_128_159     0xFFFFFFFF        // Enable I2CDriver128 to I2CDriver159
        
                #define USE_ADS1115                             // [I2cDriver13] Enable ADS1115 16 bit A/D converter (I2C address 0x48, 0x49, 0x4A or 0x4B) based on Adafruit ADS1x15 library (no library needed) (+0k7 code)
        
                // Cf. url: https://tasmota.github.io/docs/MCP230xx/
                // Vérifier activation du driver : I2cDriver22 1
                // Tester l'adresse du module MCP23XXX (adresse comprise entre 0x20 & 0x26) : I2CScan
                // Les paramètres des I/O est realisé dans le fichier mcp23xx.dat
                // Paramètres Mode 2 MCP23017
                //#define USE_MCP23XXX_DRV
                    //#define USE_MCP230xx_ADDR 0x20                  // Enable MCP23008/MCP23017 I2C Address to use (Must be within range 0x20 through 0x26 - set according to your wired setup)
                    #undef USE_DS1624                                 // [I2cDriver42] Enable DS1624, DS1621 temperature sensor (I2C addresses 0x48 - 0x4F) (+1k2 code)

                #define USE_RTC_CHIPS                                 // Enable RTC chip support and NTP server
            #endif

            // -- Internal Analog input -----------------------
            //#undef USE_ADC_VCC // Display Vcc in Power status. Disable for use as Analog input on selected devices	
        
            // -- Optional light modules ----------------------
            #define USE_LIGHT                                       // Add support for light control
            #define USE_WS2812                                      // WS2812 Led string using library NeoPixelBus (+5k code, +1k mem, 232 iram) - Disable by //
            //  #define USE_WS2812_DMA                              // ESP8266 only, DMA supports only GPIO03 (= Serial RXD) (+1k mem). When USE_WS2812_DMA is enabled expect Exceptions on Pow
                #undef USE_WS2812_RMT
                    #define USE_WS2812_RMT  1                       // ESP32 only, hardware RMT support (default). Specify the RMT channel 0..7. This should be preferred to software bit bang.
            //  #define USE_WS2812_I2S  0                           // ESP32 only, hardware I2S support. Specify the I2S channel 0..2. This is exclusive from RMT. By default, prefer RMT support
            //  #define USE_WS2812_INVERTED                         // Use inverted data signal
                #define USE_WS2812_HARDWARE  NEO_HW_WS2812          // Hardware type (NEO_HW_WS2812, NEO_HW_WS2812X, NEO_HW_WS2813, NEO_HW_SK6812, NEO_HW_LC8812, NEO_HW_APA106, NEO_HW_P9813)
                #undef USE_WS2812_CTYPE
                    #define USE_WS2812_CTYPE     NEO_GRB            // Color type (NEO_RGB, NEO_GRB, NEO_BRG, NEO_RBG, NEO_RGBW, NEO_GRBW)
        
            // -- One wire sensors ----------------------------
            #undef USE_HDMI_CEC                                     // Add support for HDMI CEC bus (+7k code, 1456 bytes IRAM)
            #define USE_DS18x20                                     // Add support for DS18x20 sensors with id sort, single scan and read retry (+2k6 code)
            //#define W1_PARASITE_POWER                             // Optimize for parasite powered sensors
            //#define DS18x20_USE_ID_AS_NAME                        // Use last 3 bytes for naming of sensors
            #define DS18x20_USE_ID_ALIAS                            // Add support aliasing for DS18x20 sensors. See comments in xsns_05 files (+0k5 code)

            // -- Serial sensors ------------------------------
            #define USE_MODBUS
            // #define USE_TASMOTA_CLIENT                       // Add support for Arduino Uno/Pro Mini via serial interface including flashing (+2k6 code, 64 mem)
                                                            // GPIO4=Slave TX / GPIO5=Slave RX
        
            // -- Capteurs & Gestion Bluetooth ------------------------------
            // #define USE_BLE_ESP32                              // Add support for ESP32 as a BLE-bridge (+9k2? mem, +292k? flash)
        
            // -- LoRaWan 868MHz ------------------------------
            #define USE_LORAWAN_BRIDGE      // Add support for LoRaWan bridge (+8k code)
            #define USE_LORA_SX126X         // Add driver support for LoRa on SX1262 based devices like LiliGo T3S3 Lora32 (+16k code)

            // -- Utilisation des WebSockets ------------------------------
            #define USE_WSSERVER

            // -- SPI sensors ---------------------------------
            #define USE_SPI                                  // Hardware SPI using GPIO12(MISO), GPIO13(MOSI) and GPIO14(CLK) in addition to two user selectable GPIOs(CS and DC)
            #ifdef USE_SPI
                #define USE_UFILESYS
                #define GUI_EDIT_FILE
                #define GUI_TRASH_FILE
        
            // -- SD Card support -----------------------------
                #define USE_SDCARD                      // mount SD Card, requires configured SPI pins and setting of `SDCard CS` gpio
                #define SDC_HIDE_INVISIBLES             // hide hidden directories from the SD Card, which prevents crashes when dealing SD created on MacOS
                #define SDCARD_CS_PIN 45                 // Not strictly necessary since the same #define happens in xdrv_50_filesystem.ino
            #endif

            // -- Rules or Script  ----------------------------
            // Select none or only one of the below defines USE_RULES or USE_SCRIPT
            #define USE_RULES                                                       // Add support for rules (+8k code)
            #ifdef USE_RULES
                #define SUPPORT_MQTT_EVENT                                          // Support trigger event with MQTT subscriptions (+1k8 code)
                #define USE_EXPRESSION                                              // Add support for expression evaluation in rules (+1k7 code)
                    #define SUPPORT_IF_STATEMENT                                    // Add support for IF statement in rules (+2k7)
                //#define USER_RULE1 "ON System#Boot DO Sensor12 S0 ENDON"          // Add rule1 data saved at initial firmware load or when command reset is executed
                //#define USER_RULE2 "<Any rule2 data>"                             // Add rule2 data saved at initial firmware load or when command reset is executed
                // USER_RULE3 "<Any rule3 data>"                                    // Add rule3 data saved at initial firmware load or when command reset is executed
                #define USE_VIEW_RULE_MEMS_AND_VARS                                 // Enable viewing of rule memories and variables in the web UI (+0k7 code)
            #endif

            // -- Compétences Audio  ----------------------------
            #define USE_I2S_ALL

            // -- Rules or Script  ----------------------------
            #ifdef USER_BACKLOG
                #undef USER_BACKLOG
            #endif
            #define USER_BACKLOG      "Backlog Hostname SERVEUR-GARAGE"
        #endif
    #endif  // USER_CONFIG_OVERRIDE_SECTION3

    /*********************************************************************************************\
     * Debug features
    \*********************************************************************************************/

    #ifdef USER_CONFIG_OVERRIDE_DEBUG
        #ifdef DEBUG_TASMOTA_CORE
            #undef DEBUG_TASMOTA_CORE
        #endif
        //#define DEBUG_TASMOTA_CORE                       // Enable core debug messages
        #ifdef DEBUG_TASMOTA_DRIVER
            #undef DEBUG_TASMOTA_DRIVER
        #endif
        #define DEBUG_TASMOTA_DRIVER                     // Enable driver debug messages
        #ifdef DEBUG_TASMOTA_SENSOR
            #undef DEBUG_TASMOTA_SENSOR
        #endif
        //#define DEBUG_TASMOTA_SENSOR                     // Enable sensor debug messages
        #ifdef USE_DEBUG_DRIVER
            #undef USE_DEBUG_DRIVER
        #endif
        //#define USE_DEBUG_DRIVER                         // Use xdrv_99_debug.ino providing commands CpuChk, CfgXor, CfgDump, CfgPeek and CfgPoke
    #endif  // USER_CONFIG_OVERRIDE_DEBUG

    /*********************************************************************************************\
     * Profiling features
     \*********************************************************************************************/

    #ifdef USER_CONFIG_OVERRIDE_PROFILING
        #ifdef USE_PROFILING
            #undef USE_PROFILING
        #endif
        //#define USE_PROFILING                            // Enable profiling

        #ifdef USE_PROFILING
            #ifdef PROFILE_THRESHOLD
                #undef PROFILE_THRESHOLD
            #endif
            //#define PROFILE_THRESHOLD            70          // Minimum duration in milliseconds to start logging
            #ifdef USE_PROFILE_DRIVER
                #undef USE_PROFILE_DRIVER
            #endif
            //#define USE_PROFILE_DRIVER                       // Enable driver profiling
            #ifdef USE_PROFILE_FUNCTION
                #undef USE_PROFILE_FUNCTION
            #endif
            //#define USE_PROFILE_FUNCTION                     // Enable driver function profiling
        #endif
    #endif  // USER_CONFIG_OVERRIDE_PROFILING

    /*********************************************************************************************\
     * Safe guard when needed defines are not done in Platformio                                                         *
    \*********************************************************************************************/

    #ifdef USER_CONFIG_OVERRIDE_SAFE_GUARD
        #ifdef OTA_URL
            #undef OTA_URL
        #endif
        #define OTA_URL ""
    #endif  // USER_CONFIG_OVERRIDE_SAFE_GUARD

    /*********************************************************************************************\
     * Post-process obsoletes
    \*********************************************************************************************/

    #ifdef USER_CONFIG_OVERRIDE_POST_PROCESS
        #ifndef FIRMWARE_SAFEBOOT
            #ifdef USE_SENDMAIL
                #undef USE_SENDMAIL
            #endif
            #define USE_SENDMAIL                             // USE_ESP32MAIL is replaced by USE_SENDMAIL
        #endif  // FIRMWARE_SAFEBOOT
    #endif  // USER_CONFIG_OVERRIDE_POST_PROCESS

    /*********************************************************************************************\
     * Mutual exclude options
    \*********************************************************************************************/
    
    #ifdef USER_CONFIG_OVERRIDE_MUTUAL_EXCLUDE
        #if defined(ESP8266) && defined(USE_DISCOVERY) && (defined(USE_MQTT_AWS_IOT) || defined(USE_MQTT_AWS_IOT_LIGHT))
            #error "Choisissez USE_DISCOVERY ou USE_MQTT_AWS_IOT. mDNS occupe trop d'espace mémoire et n'est pas nécessaire pour AWS IoT."
        #endif
    
        #if defined(USE_RULES) && defined(USE_SCRIPT)
            #error "Choisissez USE_RULES ou USE_SCRIPT. Ils ne peuvent pas être utilisés simultanément."
        #endif
    #endif  // USER_CONFIG_OVERRIDE_MUTUAL_EXCLUDE

    /*********************************************************************************************\
     * Post-process compile options for Autoconf and others
    \*********************************************************************************************/

    #ifdef USER_CONFIG_OVERRIDE_POST_PROCESS_COMPILE_OPTIONS
        //Paramètres RangeExtender
        #ifdef USE_WIFI_RANGE_EXTENDER
            #define USE_WIFI_RANGE_EXTENDER_NAPT
            #define USE_WIFI_RANGE_EXTENDER_CLIENTS
            #ifndef WIFI_RGX_SSID
            #define WIFI_RGX_SSID           "RANGE-EXTENDER-AP"
            #endif
            #ifndef WIFI_RGX_PASSWORD
            #define WIFI_RGX_PASSWORD       "Lune5676"
            #endif
            #ifndef WIFI_RGX_IP_ADDRESS
            #define WIFI_RGX_IP_ADDRESS     "192.168.4.1"
            #endif
            #ifndef WIFI_RGX_SUBNETMASK
            #define WIFI_RGX_SUBNETMASK     "255.255.255.0"
            #endif
            #ifndef WIFI_RGX_NAPT
            #define WIFI_RGX_NAPT           1
            #endif
            #define WIFI_RGX_STATE          1
        #endif

        // Paramètres Mode 1 MCP23017 (mode lancé si echec activation mode 2)
        #ifdef USE_MCP23XXX_DRV
            #define USE_MCP230xx                            // [I2cDriver22] Enable MCP23008/MCP23017 - Must define I2C Address in #define USE_MCP230xx_ADDR below - range 0x20 - 0x27 (+5k1 code)
            #ifndef USE_MCP230xx_ADDR
            #define USE_MCP230xx_ADDR 0x20                  // Enable MCP23008/MCP23017 I2C Address to use (Must be within range 0x20 through 0x26 - set according to your wired setup)
            #endif
            #define USE_MCP230xx_OUTPUT                     // Enable MCP23008/MCP23017 OUTPUT support through sensor29 commands (+2k2 code)
            #define USE_MCP230xx_DISPLAYOUTPUT              // Enable MCP23008/MCP23017 to display state of OUTPUT pins on Web UI (+0k2 code)
        #endif

        // Add support for Arduino Uno/Pro Mini via serial interface including flashing (+2k6 code, 64 mem)
        // Ajoute le support pour TasmotaClient pour le flash
        #ifdef USE_TASMOTA_CLIENT
            #define USE_TASMOTA_CLIENT_FLASH_SPEED 57600   // Usually 57600 for 3.3V variants and 115200 for 5V variants
            #define USE_TASMOTA_CLIENT_SERIAL_SPEED 57600  // Depends on the sketch that is running on the Uno/Pro Mini
        #endif

        // Si utilisation de l'ecran ILI9488
        #ifdef USE_ILI9488
            // Active SPI si ce n'est pas fait
            #ifndef USE_SPI
            #undef USE_SPI
            #endif
            #define USE_SPI
            #define USE_LVGL
            #define USE_DISPLAY                            // Add SPI Display support for 320x240 and 480x320 TFT
            #define USE_DISPLAY_LVGL_ONLY
            #define USE_LVGL_PNG_DECODER                   // include a PNG image decoder from file system (+16KB)
            #define USE_UNIVERSAL_DISPLAY
            #define USE_DISPLAY_ILI9488
            #define MAX_TOUCH_BUTTONS 16                 // Virtual touch buttons
            #define SHOW_SPLASH
                
            #define USE_XPT2046
        
            #undef USE_DISPLAY_MODES1TO5
            #undef USE_DISPLAY_LCD
            #undef USE_DISPLAY_SSD1306
            #undef USE_DISPLAY_MATRIX
            #undef USE_DISPLAY_SEVENSEG
        #endif

        // Paramètres de la gestion de fichiers
        #ifdef USE_SPI
            #define USE_UFILESYS
            #define GUI_EDIT_FILE
            #define GUI_TRASH_FILE
        #endif
        
        // Paramètres & Support MODBUS
        #ifdef USE_MODBUS
            #define USE_MODBUS_BRIDGE                        // Add support for software Modbus Bridge (+4.5k code)
            #define USE_MODBUS_BRIDGE_TCP                    // Add support for software Modbus TCP Bridge (also enable Modbus TCP Bridge) (+2k code)
            #define TASMOTAMODBUSDEBUG
        #endif
        
        #ifdef USE_BLE_ESP32                              // Add support for ESP32 as a BLE-bridge (+9k2? mem, +292k? flash)
            #define USE_MI_ESP32                             // Add support for ESP32 as a BLE-bridge (+9k2 mem, +292k flash)
            #define BLE_ESP32_ENABLE false                 // [SetOption115] Default value for SetOption115
            #define USE_IBEACON                            // Add support for Bluetooth LE passive scan of iBeacon devices (uses HM17 module)
            #define USE_IBEACON_ESP32                      // Add support for Bluetooth LE passive scan of iBeacon devices using the internal ESP32 Bluetooth module
        #endif
        
        // Utilisation des WebSockets
        // Cf. https://github.com/arendst/Tasmota/pull/23206
        #ifdef USE_WSSERVER
            #define USE_HTTPSERVER
            #define USE_WEBFILES
        #endif

        // TasMesh
        #ifdef USE_TASMESH
            // Plus d'info dans le dossier : "Tasmota\info\xdrv_57_tasmesh.md"
            #define USE_TASMESH_HEARTBEAT                    // If enabled, the broker will detect when nodes come online and offline and send Birth and LWT messages over MQTT correspondingly
            #define TASMESH_OFFLINE_DELAY  3                 // Maximum number of seconds since the last heartbeat before the broker considers a node to be offline
        #endif
        
        #ifdef USE_LORAWAN_BRIDGE
            #ifndef USE_SPI 
                #define USE_SPI                 // Add support for SPI
            #endif
            #define USE_SPI_LORA                // Add support for LoRaSend and LoRaCommand (+4k code)
            #if !defined(USE_LORA_SX126X) && !defined(USE_LORA_SX127X)
                #define USE_LORA_SX126X         // Configuration par défaut SX1262
            #endif
            // #define USE_LORA_SX126X          // Add driver support for LoRa on SX126x based devices like LiliGo T3S3 Lora32 (+16k code)
            // #define USE_LORA_SX127X          // Add driver support for LoRa on SX127x based devices like M5Stack LoRa868, RFM95W (+5k code)
            #define USE_LORA_SX126X_DEBUG

            // Modèle qui fonctionne avec ESP32S3 + SX1262
            // {"NAME":"LilygoT3S3-SX126x","GPIO":[0,0,0,672,0,736,704,10656,10688,0,0,0,0,0,0,0,0,0,0,0,0,0,10784,10720,0,0,0,0,0,0,0,0,0,0,0,0,0,0],"FLAG":0,"BASE":1}
        #endif
        
        #ifdef USE_AUTOCONF
            #ifndef USE_BERRY
                #define USE_BERRY
            #endif
            #ifndef USE_WEBCLIENT_HTTPS
                #define USE_WEBCLIENT_HTTPS
            #endif
            #ifndef USE_MQTT_TLS
                #define USE_MQTT_TLS
            #endif

            #ifdef USE_SONOFF_SPM
                #define USE_ETHERNET
            #endif
        #endif // USE_AUTOCONF

        #ifdef USE_I2S_ALL
            #ifdef USE_I2S
                #undef USE_I2S
            #endif
            #define USE_I2S
            #ifdef USE_I2S_AUDIO
                #undef USE_I2S_AUDIO
            #endif
            #define USE_I2S_AUDIO
            #ifdef USE_I2S_MIC
                #undef USE_I2S_MIC
            #endif
            #define USE_I2S_MIC
            #ifdef USE_SHINE
                #undef USE_SHINE
            #endif
            #define USE_SHINE
            #ifdef MP3_MIC_STREAM
                #undef MP3_MIC_STREAM
            #endif
            #define MP3_MIC_STREAM
            #ifdef USE_I2S_AUDIO_BERRY
                #undef USE_I2S_AUDIO_BERRY
            #endif
            #define USE_I2S_AUDIO_BERRY
            #ifdef USE_I2S_AAC
                #undef USE_I2S_AAC
            #endif
            #define USE_I2S_AAC
            #ifdef USE_I2S_OPUS
                #undef USE_I2S_OPUS
            #endif
            #define USE_I2S_OPUS
            #ifdef USE_I2S_SAY_TIME
                #undef USE_I2S_SAY_TIME
            #endif
            #define USE_I2S_SAY_TIME
            #ifdef USE_I2S_NO_DAC
                #undef USE_I2S_NO_DAC
            #endif
            //#define USE_I2S_NO_DAC
            #ifdef USE_I2S_RTTTL
                #undef USE_I2S_RTTTL
            #endif
            #define USE_I2S_RTTTL
            #ifdef I2S_BRIDGE
                #undef I2S_BRIDGE
            #endif
            // #define I2S_BRIDGE                               // Add support for UDP PCM audio bridge
            // #define I2S_BRIDGE_PORT    6970                  // Set bridge port (default = 6970)
        #endif // USE_I2S_ALL

        #ifdef USE_SHUTTER
            #ifdef SHUTTER_SUPPORT
                #undef SHUTTER_SUPPORT
            #endif
            #define SHUTTER_SUPPORT        true             // [SetOption80] Enable shutter support
        #endif // USE_SHUTTER

        // Utilisations de modules RTC (ex: DS3231)
        #ifdef USE_RTC_CHIPS     
            #ifndef USE_I2C
                #define USE_I2C
            #endif               
            #ifndef USE_RTC_CHIPS 
                #define USE_RTC_CHIPS               // Enable RTC chip support and NTP server
            #endif
            #ifndef USE_DS3231
                #define USE_DS3231                  // [I2cDriver26] Enable DS3231 RTC (I2C address 0x68) (+1k2 code)
                #define USE_RTC_ADDR    0x68   
            #endif
        #endif  // USE_RTC_CHIPS
    #endif  // USER_CONFIG_OVERRIDE_POST_PROCESS_COMPILE_OPTIONS
#endif  // _USER_CONFIG_OVERRIDE_H_