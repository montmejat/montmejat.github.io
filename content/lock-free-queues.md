---
title: Lock-Free Queues
slug: lock-free-queues
tree:
  parent: Robotics
  blurb: Sharing without waiting
---

A real-time thread cannot take a mutex that a lower-priority thread might hold.
If it does, it waits for a thread that isn't being scheduled — priority
inversion — and the deadline is gone. So data has to cross between threads
without anyone blocking.

## The single-producer, single-consumer ring

The workhorse. A fixed-size array allocated up front, plus two indices: a write
position owned exclusively by the producer, and a read position owned
exclusively by the consumer. Neither thread ever writes the other's index, so
there is nothing to contend over.

The correctness rests on memory ordering. The producer writes the payload into a
slot, then publishes the slot by storing the new write index with **release**
semantics. The consumer loads that index with **acquire** semantics. The pairing
guarantees that if the consumer sees the new index, it also sees every write that
happened before it was published.

```cpp
// producer
buffer[write & mask] = value;
write_index.store(write + 1, std::memory_order_release);

// consumer
auto w = write_index.load(std::memory_order_acquire);
if (read != w) {
    auto value = buffer[read & mask];
    read_index.store(read + 1, std::memory_order_release);
}
```

Sizing the buffer to a power of two lets the wrap be a mask instead of a modulo.
`volatile` is not a substitute for atomics here: it prevents the compiler
caching the value in a register but says nothing about ordering or about what
other cores observe.

## False sharing

If the read and write indices land on the same 64-byte cache line, the two cores
fight over that line continuously even though they touch different variables —
the hardware grants exclusive ownership per line, not per variable. The queue
becomes slower than a mutex.

The fix is to pad them apart:

```cpp
alignas(64) std::atomic<size_t> write_index;
alignas(64) std::atomic<size_t> read_index;
```

This is the most common reason a hand-written lock-free structure benchmarks
badly.

## Lock-free, wait-free, and what you actually need

*Lock-free* means the system as a whole always makes progress — some thread
completes even if others stall. *Wait-free* is stronger: every thread finishes in
a bounded number of steps, regardless of what the others do. An SPSC ring is
wait-free on both sides, which is why it suits a control loop: the bound is
known.

Multi-producer variants need compare-and-swap loops, which are lock-free but not
wait-free — a thread can be forced to retry indefinitely under contention. Worth
avoiding on the real-time side.

## When you want the latest value, not a queue

Much of the time a control loop doesn't want a queue at all. It wants the most
recent joint state, and older samples are worthless. A queue in that situation
just adds a way to fall behind.

The right structure is a **seqlock**. The writer increments a sequence counter
before writing and again after. The reader samples the counter, reads the data,
samples the counter again, and retries if it changed or if it was odd — odd
meaning a write was in progress.

```cpp
// reader
do {
    s1 = seq.load(std::memory_order_acquire);
    snapshot = shared_state;
    s2 = seq.load(std::memory_order_acquire);
} while (s1 != s2 || (s1 & 1));
```

The writer never blocks and never waits for readers, which is exactly what you
want when the writer is the thing with the deadline. The cost is that a reader
can be forced to retry, so it isn't suitable in the other direction — don't put
your control loop on the reading side of a seqlock written by something
unbounded.

## Logging without touching disk

The same primitive solves telemetry. The real-time thread pushes fixed-size
records into a preallocated ring and returns immediately; a lower-priority thread
drains it and does the formatting, compression and file I/O. If the ring fills,
the real-time side drops records and increments a counter rather than blocking —
losing telemetry is always better than missing a cycle.
