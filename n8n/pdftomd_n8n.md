{
  "name": "PDF to MD Parser",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "fetch-paper",
        "options": {
          "responseCode": {
            "values": {}
          }
        }
      },
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2.1,
      "position": [
        -16,
        0
      ],
      "id": "c5ae26f6-e7af-475d-adcd-8463fbceb16a",
      "name": "Webhook",
      "webhookId": "2752d20e-7afc-4c8c-8af4-d63dbad9bbee"
    },
    {
      "parameters": {
        "url": "={{ $json.body.url }}",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [
            {
              "name": "User-Agent",
              "value": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
          ]
        },
        "options": {
          "response": {
            "response": {
              "responseFormat": "file"
            }
          }
        }
      },
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.4,
      "position": [
        416,
        0
      ],
      "id": "bf74be76-22b5-470f-8c7f-969cfdffa922",
      "name": "PDF Downloader"
    },
    {
      "parameters": {
        "operation": "write",
        "fileName": "=/workspace/obsidian_brain/Research & Syntheses/{{ $('Webhook').item.json.body.folder_name }}/{{ $('Webhook').item.json.body.title }}.md",
        "options": {}
      },
      "type": "n8n-nodes-base.readWriteFile",
      "typeVersion": 1.1,
      "position": [
        1232,
        0
      ],
      "id": "61fe8252-8e45-4a75-bad6-3ae78ced8268",
      "name": "Read/Write Files from Disk"
    },
    {
      "parameters": {
        "operation": "toText",
        "sourceProperty": "final_markdown",
        "binaryPropertyName": "=data",
        "options": {
          "fileName": "={{ $('Webhook').item.json.body.title }}.md"
        }
      },
      "type": "n8n-nodes-base.convertToFile",
      "typeVersion": 1.1,
      "position": [
        1040,
        0
      ],
      "id": "d869ff35-bf9e-4ebb-a29f-e81eac8d8ee3",
      "name": "Convert to File"
    },
    {
      "parameters": {
        "amount": 10
      },
      "type": "n8n-nodes-base.wait",
      "typeVersion": 1.1,
      "position": [
        192,
        0
      ],
      "id": "06cc0d38-5b63-4a98-8752-81023898b161",
      "name": "Wait",
      "webhookId": "88ca5cf7-e928-4df2-9e62-df7beaa4bcc2"
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://pdf_service:5001/v1/convert/file",
        "sendBody": true,
        "contentType": "multipart-form-data",
        "bodyParameters": {
          "parameters": [
            {
              "parameterType": "formBinaryData",
              "name": "file",
              "inputDataFieldName": "data"
            }
          ]
        },
        "options": {
          "timeout": 300000
        }
      },
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.4,
      "position": [
        624,
        0
      ],
      "id": "e432f47a-4a7c-4a3c-9766-95cc70a12d7e",
      "name": "PyMuPDF4LLM Parser PDF to MD"
    },
    {
      "parameters": {
        "assignments": {
          "assignments": [
            {
              "id": "4dd54b2d-2075-4dc7-8653-05a79fe8d07d",
              "name": "final_markdown",
              "value": "=---\ncreate-date: {{ $now.format('yyyy-MM-dd, HH:mm:ss') }}\ntype: Resource\ntags:\n  - literature-rag/{{ $('Webhook').item.json.body.folder_name }}\nstatus: uncompleted\norder:\nparent:\n---\n\n{{ $json.document.md_content }}",
              "type": "string"
            }
          ]
        },
        "options": {}
      },
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.4,
      "position": [
        832,
        0
      ],
      "id": "ff5b1be2-6858-4fb0-9b6f-82f663dfd054",
      "name": "Edit Fields"
    }
  ],
  "pinData": {},
  "connections": {
    "Webhook": {
      "main": [
        [
          {
            "node": "Wait",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "PDF Downloader": {
      "main": [
        [
          {
            "node": "PyMuPDF4LLM Parser PDF to MD",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Convert to File": {
      "main": [
        [
          {
            "node": "Read/Write Files from Disk",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Wait": {
      "main": [
        [
          {
            "node": "PDF Downloader",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "PyMuPDF4LLM Parser PDF to MD": {
      "main": [
        [
          {
            "node": "Edit Fields",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Edit Fields": {
      "main": [
        [
          {
            "node": "Convert to File",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  },
  "active": true,
  "settings": {
    "executionOrder": "v1",
    "binaryMode": "separate",
    "availableInMCP": false
  },
  "versionId": "6584169c-c743-4037-835e-2b4ad882e16b",
  "nodeGroups": [],
  "id": "IIPY31f64iF2Qy21",
  "tags": []
}
