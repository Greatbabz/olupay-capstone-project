# OluPay 2.0 — AWS Capstone Project

![AWS Lambda](https://img.shields.io/badge/AWS-Lambda-FF9900?style=for-the-badge&logo=awslambda&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Aurora MySQL](https://img.shields.io/badge/AWS-Aurora_MySQL-4053D6?style=for-the-badge&logo=amazondynamodb&logoColor=white)
![Serverless](https://img.shields.io/badge/Architecture-Serverless-FD5750?style=for-the-badge)
![API Gateway](https://img.shields.io/badge/AWS-API_Gateway-FF4F8B?style=for-the-badge)
![ElastiCache](https://img.shields.io/badge/AWS-ElastiCache_Redis-DC382D?style=for-the-badge)

> BaseStack Academy · AWS Cloud Accelerator · Cohort 1 · Capstone Project · Scenario A

---

## Overview

OluPay has grown from 400,000 to 2 million users across Nigeria. The old infrastructure could not handle salary day (25th of every month) without manual intervention. This project rebuilds the entire infrastructure from scratch on AWS — multi-AZ, fully managed, and cost-optimised to run under **$200/month** at steady state with **zero manual intervention** during peak traffic.

**Key constraint:** Every architectural decision is justified in both cost AND security terms.

---

## Architecture

```
Internet / Client
       │
       ▼
Application Load Balancer (olupay-alb)
       │
  ─────┴──────────────────────────────────
  │                                       │
  ▼                                       ▼
EC2 Web Tier (ASG)              API Gateway HTTP API
t2.micro · CPU 60% scale        POST /payments
  │                                       │
  │                                       ▼
  │                            Lambda: ProcessPayment
  │                              │        │
  │                              ▼        ▼
  │                           Aurora    DynamoDB
  │                           MySQL     Merchant
  │                           Ledger    Catalogue
  │                              │
  │                              ▼
  │                            SQS: PaymentProcessingQueue
  │                              │
  │                              ▼
  │                            Lambda: SendNotification
  │                              │
  │                              ▼
  │                            SNS: OluTech-Alerts
  │                              │
  │                              ▼
  │                            Email notification
  │
  ├── ElastiCache Redis (OTP cache · TTL 5 min)
  ├── S3 (financial reports · versioning · SSE · CRR)
  └── CloudWatch (dashboard · alarms · Logs Insights)

All services sit inside a custom VPC (10.0.0.0/16)
across 2 AZs with least-privilege IAM roles.
```

## Solution Architecture

<p align="center">
  <img src="./architecture-diagram.png" alt="OluPay AWS Architecture" width="1000">
</p>

The architecture uses API Gateway, Lambda, SQS, SNS, Aurora MySQL, DynamoDB, ElastiCache Redis, CloudWatch, and S3 to deliver a highly available and scalable payment platform.

---

## Services Used

| Layer | Service | Role |
|---|---|---|
| Network | VPC, IGW, NAT Gateway | Custom VPC · 4 subnets across 2 AZs |
| Security | IAM, Security Groups | Least-privilege roles · no wildcard resources |
| Compute | EC2, ALB, Auto Scaling | Web tier · scale-out on CPU > 60% |
| Storage | S3 | Financial reports · versioning · SSE-S3 · CRR to af-south-1 |
| Database | Aurora MySQL | Payments ledger · private subnet · no public access |
| NoSQL | DynamoDB | Merchant catalogue · GSI on MerchantCategory |
| Cache | ElastiCache Redis | OTP caching · TTL 5 min · cache-aside pattern |
| Serverless | Lambda (Python 3.12) | ProcessPayment + SendNotification · separate responsibilities |
| API | API Gateway (HTTP) | POST /payments · live endpoint |
| Messaging | SQS | Async decoupling Lambda 1 → Lambda 2 |
| Alerting | SNS | Email alerts for all payments |
| Observability | CloudWatch | Dashboard · alarms · Logs Insights · log streams |

---

## Architectural Decisions

### Why Aurora over standard RDS?
Aurora MySQL delivers up to 5x the throughput of standard MySQL, critical for salary day spikes where 2 million users transact simultaneously. Aurora's storage auto-scales from 10GB to 128TB without manual intervention, eliminating capacity planning. Automatic failover completes in under 30 seconds vs RDS Multi-AZ's 60-120 seconds, meeting our 99.99% uptime SLA. At steady state, Aurora Serverless scales down off-peak, keeping us under $200/month.

### Why ElastiCache Redis for OTP?
OTP lookups are the highest-frequency read operation at salary day — up to 2 million requests per hour. Redis caches each OTP with a 5-minute TTL using the cache-aside pattern: check cache first (hit = <1ms response), on miss generate OTP and write to cache. This offloads ~80% of OTP reads from Aurora, reducing DB costs and preventing connection pool exhaustion during peak.

### Why SQS between Lambda 1 and Lambda 2?
Direct Lambda-to-Lambda calls create tight coupling — if SendNotification fails, ProcessPayment fails too. SQS decouples them: ProcessPayment writes to the queue and returns 200 immediately. SendNotification consumes the queue asynchronously, retrying on failure without affecting the payment response time. Visibility timeout is set to 30 seconds — greater than Lambda's expected duration.

### Why On-Demand DynamoDB?
The merchant catalogue has unpredictable read patterns. On-demand capacity eliminates idle provisioned capacity costs during off-peak hours while handling salary day spikes automatically. No capacity planning required.

---

## Salary Day Handling (25th of Every Month)

1. Traffic spike detected → CloudWatch CPU alarm fires at 60%
2. ASG scale-out triggered → new EC2 instances launch from template in <3 minutes
3. ALB distributes load across all healthy instances
4. Redis absorbs OTP read spike (cache-aside — no DB hit on cache hit)
5. SQS queues notification backlog — no Lambda timeout pressure
6. Aurora handles write surge via connection pooling
7. Spike ends → ASG scales in → cost returns to baseline

**Zero manual intervention required.**

---

## Cost Breakdown (Steady State)

| Service | Config | Monthly Cost |
|---|---|---|
| EC2 (steady state) | 1x t2.micro On-Demand | ~$8 |
| ALB | 1 ALB + LCU charges | ~$18 |
| Aurora MySQL | db.t3.medium serverless | ~$60 |
| ElastiCache Redis | cache.t3.micro | ~$12 |
| NAT Gateway | 1 NAT + data transfer | ~$35 |
| S3 | Standard + Standard-IA lifecycle | ~$5 |
| Lambda + API GW | 2M requests/month | ~$1 |
| SQS + SNS | Free tier covers usage | ~$0 |
| CloudWatch | Basic metrics + logs | ~$5 |
| **TOTAL** | | **~$144/month ✅** |

Budget: $200/month. Actual: ~$144/month. **Buffer: $56/month.**

---

## How to Deploy

### Prerequisites
- AWS account with admin access
- AWS CLI configured (`aws configure`)
- Python 3.12

### Step 1 — VPC & Networking
```
VPC CIDR:          10.0.0.0/16
Public subnet 1:   10.0.1.0/24  (us-east-1a)
Public subnet 2:   10.0.2.0/24  (us-east-1b)
Private subnet 1:  10.0.10.0/24 (us-east-1a)
Private subnet 2:  10.0.20.0/24 (us-east-1b)
IGW:               attached to VPC
NAT Gateway:       in public subnet 1
Public RT:         0.0.0.0/0 → IGW
Private RT:        0.0.0.0/0 → NAT
```

### Step 2 — Security Groups
```
olupay-web-sg:     HTTP 80, HTTPS 443 from 0.0.0.0/0
                   SSH 22 from olupay-bastion-sg
olupay-db-sg:      MySQL 3306 from olupay-web-sg
                   Redis 6379 from olupay-web-sg
olupay-bastion-sg: SSH 22 from your IP only
```

### Step 3 — IAM Roles (no wildcard * resources)
```
olupay-lambda-role:  DynamoDB, SQS, SNS (specific ARNs)
olupay-ec2-role:     S3 read, CloudWatch logs
olupay-rds-role:     RDS Enhanced Monitoring only
```

### Step 4 — Databases
```
Aurora MySQL:
  Cluster:        olupay-aurora-cluster
  Engine:         Aurora MySQL 8.0
  Instance:       db.t3.medium
  Subnet:         private subnets
  Public access:  NO

DynamoDB:
  Table:          olupay-merchants
  Partition key:  MerchantID (String)
  Sort key:       CreatedAt (String)
  GSI:            MerchantCategory-index
  Capacity:       On-demand

ElastiCache Redis:
  Name:           olupay-redis
  Node:           cache.t3.micro
  Subnet:         private subnets
  TLS:            enabled
```

### Step 5 — Lambda Functions
```
olupay-process-payment:    Handles POST /payments
                           Writes to DynamoDB + SQS
olupay-send-notification:  Triggered by SQS
                           Publishes to SNS
```

Update these values in `lambda_process_payment.py`:
```python
QueueUrl = 'https://sqs.us-east-1.amazonaws.com/YOUR_ID/PaymentProcessingQueue'
```

Update this value in `lambda_send_notification.py`:
```python
TopicArn = 'arn:aws:sns:us-east-1:YOUR_ID:OluTech-Alerts'
```

### Step 6 — API Gateway
```
Type:      HTTP API
Name:      olupay-api
Route:     POST /payments → olupay-process-payment
Stage:     $default
```

### Step 7 — S3
```
Bucket:       olupay-capstone-bucket
Versioning:   Enabled
Encryption:   SSE-S3
Lifecycle:    Transition to Standard-IA after 30 days
Replication:  Cross-region to af-south-1
```

---

## API Usage

### POST /payments

**Endpoint:**
```
POST https://e01nkvn4r0.execute-api.us-east-1.amazonaws.com/payments
```

**Request body:**
```json
{
  "sender": "Alice",
  "recipient": "Bob",
  "amount": 5000,
  "reference": "TXN-001"
}
```

**Success response (200):**
```json
{
  "message": "Payment processed successfully",
  "reference": "TXN-001",
  "timestamp": "2026-06-26T21:42:54.249828",
  "status": "Completed"
}
```

**Large payment (>100,000) — triggers SNS email:**
```json
{
  "sender": "Alice",
  "recipient": "Bob",
  "amount": 500000,
  "reference": "TXN-002"
}
```

### Test with PowerShell
```powershell
Invoke-WebRequest `
  -Uri "https://e01nkvn4r0.execute-api.us-east-1.amazonaws.com/payments" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"sender":"Alice","recipient":"Bob","amount":5000,"reference":"TXN-001"}'
```

### Test with curl
```bash
curl -X POST https://e01nkvn4r0.execute-api.us-east-1.amazonaws.com/payments \
  -H "Content-Type: application/json" \
  -d '{"sender":"Alice","recipient":"Bob","amount":5000,"reference":"TXN-001"}'
```

---

## Repository Structure

```
olupay-capstone/
├── README.md
├── architecture-diagram.png
├── lambda_process_payment.py
└── lambda_send_notification.py
```

---

## Portfolio

Built as part of the **BaseStack Academy AWS Cloud Accelerator** — Cohort 1 Capstone.

Live API: `https://e01nkvn4r0.execute-api.us-east-1.amazonaws.com/payments`

> Built by Oluwatoba Babalola | [X / Twitter](https://x.com/Itz_Greatbabz) | [Portfolio](http://olupay-capstone-bucket-070340244863-us-east-1-an.s3-website-us-east-1.amazonaws.com)
