# CS 6: API sequence diagram

**Request:** "Sequence diagram: client requests a job, service validates, queues it, worker runs it, client polls." One scenario (happy path) plus one retry frame.
**Type:** sequence diagram. Solid = synchronous call, dashed = return, open head = asynchronous message.

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API service
    participant Q as Job queue
    participant W as Worker
    participant S as Storage
    C->>A: POST /jobs (payload)
    A->>A: validate payload
    A->>Q: enqueue(job_id)
    A-->>C: 202 Accepted (job_id)
    Q--)W: deliver(job_id)
    loop up to 3 attempts
        W->>S: read inputs
        S-->>W: data
        W->>W: run job
    end
    W->>S: write result
    W--)Q: ack(job_id)
    C->>A: GET /jobs/{job_id}
    A-->>C: 200 OK (status, result_url)
```
**Checks:** async delivery (`--)`) vs synchronous calls; the 202 returns before the work happens; polling is a separate synchronous exchange; failure after 3 attempts is a different scenario (not drawn - add an `alt` frame if needed).
**Caption:** Message sequence for asynchronous job submission. The API acknowledges the request immediately (202) after enqueueing; a worker processes the job asynchronously, with up to three attempts, and stores the result, which the client retrieves by polling.
