---
title: Real-Time Linux
slug: real-time-linux
tree:
  parent: Real-time systems
  blurb: Making a loop land on time
---

A robot control loop has a deadline. At 1 kHz you get one millisecond to read the
bus, run the controller, and write back; miss it and the joint gets a stale
command. What makes this hard on Linux is not raw speed — a modern CPU does the
arithmetic in microseconds — but *variance*. The interesting number is never the
average iteration time, it's the worst one.

## Latency and jitter are different problems

Latency is how long something takes. Jitter is how much that duration varies
between iterations.

A path that always takes 50 µs is usually fine: you budget for it and move on. A
path that normally takes 5 µs but occasionally takes 900 µs is not fine, even
though it's ten times faster on average. The controller has to be correct in the
worst case, so the tail of the distribution is the thing that matters.

This is why an average is close to useless here. Report percentiles — p99, p99.9,
and the maximum observed — and always state how long you measured for. A maximum
over ten seconds and a maximum over ten hours are different claims.

## Where the time actually goes

On a general-purpose kernel a handful of things can stall a thread that was
supposed to be running:

- **Preemption by another task.** The scheduler picks something else.
- **Interrupts.** A network card or timer IRQ runs on your core, on top of your
  thread, whenever it feels like it.
- **Kernel sections that can't be preempted.** Your high-priority thread is
  ready, but the kernel is inside a critical section and won't yield yet.
- **Page faults.** Touching memory that isn't resident means a trip to the
  allocator, or worse, to disk.
- **Cache and TLB misses.** Nothing stalled you logically, but the data isn't in
  cache and the CPU waits on memory.
- **Frequency scaling and thermal throttling.** The core is running slower than
  it was last iteration.

Each of these is fixable, and the fixes are mostly configuration rather than
code.

## PREEMPT_RT

`PREEMPT_RT` is the real-time patch set for Linux, largely merged into mainline
as of 6.12. It makes most kernel spinlocks preemptible and moves interrupt
handling into schedulable kernel threads, so a high-priority task can preempt
almost anything the kernel is doing.

It does not make anything faster on average. What it does is collapse the worst
case — which is exactly the number a control loop cares about. On a stock kernel
worst-case scheduling latency is often hundreds of microseconds or worse; with
`PREEMPT_RT` plus the isolation described below it typically lands in the low
tens.

## Getting a core to yourself

The most effective change is usually not in your program at all. It's telling
the kernel to leave one core alone:

```text
isolcpus=3        # keep the general scheduler off core 3
nohz_full=3       # stop the periodic timer tick there
rcu_nocbs=3       # move RCU callback processing elsewhere
irqaffinity=0-2   # route interrupts to the other cores
```

On a heterogeneous SoC — a cluster of fast cores and a cluster of efficient ones
— this matters twice over, because a thread migrated onto an efficiency core
will miss a deadline it would have made on a performance core. Pin deliberately.

## Scheduling policy

Two policies matter:

- **`SCHED_FIFO`** — a fixed priority, and the thread runs until it blocks or is
  preempted by something higher. Simple and predictable. The catch is that a
  runaway FIFO thread can starve everything below it.
- **`SCHED_DEADLINE`** — you declare a period, a worst-case runtime and a
  deadline, and the kernel admits the task only if the set is schedulable. More
  honest about what you actually need, less widely used.

Priorities want to be assigned by how tight the deadline is, not by how
important the work feels. The bus loop is tighter than the state publisher,
which is tighter than logging.

## What you cannot do inside the loop

Once the thread is running, correctness comes from what the loop *doesn't* do:

- **No allocation.** `malloc` can take a lock and can fault in new pages.
  Pre-allocate everything before the loop starts.
- **No page faults.** Call `mlockall(MCL_CURRENT | MCL_FUTURE)` at startup so
  pages stay resident, and touch your buffers once up front.
- **No unbounded blocking.** Any mutex shared with a lower-priority thread needs
  priority inheritance (`PTHREAD_PRIO_INHERIT`), or you get priority inversion:
  your high-priority thread waits on a lock held by a low-priority thread that
  isn't being scheduled.
- **No I/O.** No printing, no file writes, no syscalls you didn't budget for.
  Push logging into a lock-free ring buffer and let a lower-priority thread
  drain it.

## Waiting for the next cycle

The periodic wait wants to be absolute, not relative. Sleeping for "one
millisecond from now" accumulates drift, because *now* is already late by
whatever the previous iteration overran:

```c
struct timespec next;
clock_gettime(CLOCK_MONOTONIC, &next);

for (;;) {
    next.tv_nsec += period_ns;
    /* normalise tv_sec / tv_nsec here */

    clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &next, NULL);

    /* one cycle of work */
}
```

Waking on an absolute timestamp means a late iteration doesn't push the next one
late as well. Errors stop compounding.

The alternative at the extreme end is not to sleep at all: spin on a counter and
never yield the core. That buys tens of nanoseconds instead of a few
microseconds, at the cost of burning a core continuously, and it's the trick
behind the low-latency messaging layers used in trading and in kernel-bypass
networking.

## Measuring it

`cyclictest`, from `rt-tests`, measures the gap between when a thread asked to
wake and when it actually ran. That's the floor under everything else:

```bash
cyclictest -m -p80 -i1000 -a3 -t1 -h1000 -q -D 10m
```

`-h` gives a histogram, which is the part worth looking at — a long thin tail
and a fat shoulder are different problems.

For your own loop, timestamp the top of each cycle with `CLOCK_MONOTONIC`, push
the delta into a pre-allocated ring buffer, and dump it after the run. Never
format or print inside the loop; the measurement must not perturb the thing
being measured.

Two rules make the resulting number mean something:

**Measure under load.** An idle system tells you what your machine can do, not
what it does. Run it with everything attached that will be attached in
production.

**Separate the sources.** Thread wake-up jitter, fieldbus cycle jitter, and
end-to-end round-trip time are three different measurements with three different
causes. A single number that mixes them can't be acted on.
