---
title: EtherCAT
slug: ethercat
tree:
  parent: Robotics
  blurb: Fieldbus, PDOs and the state machine
---

EtherCAT is an Ethernet-based fieldbus for connecting a controller to motor
drives and I/O. It is the layer immediately under a robot's control loop: the
loop computes a command, and EtherCAT is how that command reaches the drive and
how the drive's state comes back.

## Processing on the fly

The thing that makes it fast is that slaves do not receive, store, and forward
frames. A single frame is sent by the master and passes through every slave in
the network; each slave reads the bytes addressed to it and writes its own reply
*into the frame as it passes through*, in hardware, with a delay on the order of
a microsecond. The frame comes back to the master having visited everyone.

So the cycle cost is roughly one frame transit, not N hops of switching latency.
A network of thirty drives can be serviced in well under a millisecond.

## The process image

The master doesn't address slaves one at a time during the cyclic exchange. An
FMMU (fieldbus memory management unit) on each slave maps that slave's local
registers into a shared logical address space, so from the master's side the
whole network looks like one contiguous block of memory — the process image.
Read a byte range, get every drive's status; write another range, command them
all.

Two kinds of data travel over it:

- **PDOs** (process data objects) — the cyclic payload. Actual position,
  velocity, torque, status word out; target position and control word in. This
  is what the control loop touches every cycle.
- **SDOs** (service data objects) — acyclic configuration, sent through a
  mailbox. Gear ratios, limits, PDO mapping itself. Used at startup, not in the
  loop.

With CANopen over EtherCAT (CoE), the drive exposes a CiA 402 object dictionary:
`0x6040` control word, `0x6041` status word, `0x6060` mode of operation,
`0x607A` target position. The modes that matter for a high-rate loop are the
cyclic synchronous ones — CSP, CSV, CST for position, velocity and torque.

## The state machine

Slaves move through four states, and bring-up problems are usually a slave
refusing to advance:

```text
INIT      no communication beyond basic registers
PRE-OP    mailbox works; SDO configuration happens here
SAFE-OP   process data inputs valid, outputs not yet applied
OP        outputs applied — the drive acts on commands
```

A slave stuck in PRE-OP or dropping back to SAFE-OP almost always means a
mismatch between the PDO mapping the master configured and what the slave
expects, or a missing mandatory SDO. Useful practice is to report *which* slave
failed to advance rather than that the transition failed, because on a
thirty-node network that difference is an hour of debugging.

## The working counter

Every datagram carries a working counter. Each slave that successfully processes
its portion increments it. The master knows what the total should be, so a
mismatch is an immediate, cheap, per-cycle health check: a slave has dropped off,
or a cable is marginal, or something is not in the state you think it is.

Checking the working counter every cycle, and treating a mismatch as a fault
rather than logging it and continuing, is the single most useful piece of
defensive code in an EtherCAT master.

## Distributed clocks

Frames reach slaves at different times, which means that without help, thirty
drives would act on their commands at thirty slightly different instants. The
distributed clock mechanism fixes this. One slave's clock is the reference; the
master measures propagation delay to every other slave, computes offsets, and
then continuously compensates drift. Slaves then generate a local SYNC0 event,
and they all act on that — simultaneously — rather than on frame arrival.

This is a different concern from loop jitter and worth measuring separately. Your
thread can wake perfectly on time and the bus can still be badly synchronised,
or the reverse.
