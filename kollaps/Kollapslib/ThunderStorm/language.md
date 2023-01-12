# Dynamic topology language features

In order to save you some time designing your experiments, we provide some high-level abstractions for often used scenarios. More precisely, we offer a generator that takes as an input your static topology and some high-level commands (such as `partition the network in two at 50s`) and generates the corresponding `schedule` elements that can then be added to the dynamic section of your topology.

## Instant and period events

Similarly to the [Splay churn generator](https://github.com/splay-project/splay/tree/master/tools/churn_gen), we differentiate between _instant_ and _period_ events. An instant event might be a certain node crashing (and staying down), a period event might be a link flapping (rapidly going up and down) for 2 minutes.

For all events, the very basic syntax is `time? action arguments*`

## Finite and infinite experiments

In order to not end up with infinitely long dynamic topologies while still supporting period events without a specified start and end time, there are semantics to end the whole experiment after a certain period of time:

```
at 240s quit
```

If there is at least one period event without specified start and end time, one (and only one) `quit` event is mandatory.

## Entities with dynamic behaviour

Generally, all services, links, and bridges can be scheduled to exhibit dynamic behaviour.
These are the high-level dynamic concepts that certain entities can exhibit:

| Entity        | Actions           |
| ------------- |----------------|
| Service      | join,

 leave, crash, disconnect, reconnect |
| Bridge      | join, leave      |
| Link | join, leave, change any of [latency, bandwidth, jitter, packet loss]      |

## Scope of dynamic behaviour

We provide support for having events happen across the whole network or on a certain set of entities. Of course, the user can always manually add events as specific as they want targeting one or multiple entities.

### Network-wide events

In order to simulate network-wide events, such as a complete power outage of the datacenter, or sudden background traffic on all links, events target all possible targets if no target is specified:

```
at 120s crash
at 130s join #power outage
at 100s set latency=200% bandwidth=50%
```

### Grouping entities
In order to make it easier to schedule such events together, all these entities can be _tagged_ with an arbitrary number of tags; certain actions can then be scheduled for all entities with a certain tag. We could emulate, for example, a scheduled software update for all nodes and make it non-overlapping with regard to some software versions like this:

```
<service name="clientv1" image="warpenguin.no-ip.org/alpineclient:1.1" tags="v1" command="['server', '0', '0']"/>
<service name="clientv2" image="warpenguin.no-ip.org/alpineclient:1.2" tags="v2" command="['server', '0', '0']"/>
<service name="clientv3" image="warpenguin.no-ip.org/alpineclient:1.3" tags="v3" command="['server', '0', '0']"/>

<schedule tags="v1 v2" time="100.0s" action="leave">
<schedule tags="v1 v2" time="200.0s" action="join">
<schedule tags="v3" time="400.0s" action="leave">
<schedule tags="v3" time="600.0s" action="join">
```

(Indeed, it has been noted in the literature that software upgrades are one of the most frequent reasons for network "failures".)

If an action is specified that does not apply to an entity - such as changing bandwidth for a service -, that action is simply discarded.

### Local events

The full range of expressions listed in the [wiki](https://github.com/miguelammatos/NEED/wiki/Dynamic-experiments) (and in the table above) is available on the entity level.

## Idioms

Here, we present three shorthands that abbreviate often-used patterns. **(Further suggestions welcome)**

### Partitioning the network

One of the most dangerous scenarios in real-life distributed applications is the partitioning of the whole network, i.e. parts of the network being _completely unreachable_ by other parts.

We provide the keyword `partition` that takes as arguments `;`-separated lists of ` `-separated lists of entities that are still reachable amongst each other. We then compute a set of minimal cuts to obtain the described partition. For example, we would have:

```
at 120s partition frontend;backend database
```

### Link flapping

Links are identified in the topology description language as having an `origin` and `dest` element, respectively. As the only element that is defined by two names (of other elements), my suggestion is to identify links by those two names in the language, separated by `--`.

Link flapping is considered to be one of the biggest technical problems with individual links. Definitions of what exactly constitutes link flapping vary in literature. We support the `flap` keyword:

```
from 0s to 120s server--s1 flap freq 0.5s
```

This would be compiled to atomic events like this:

```
<schedule origin="server" dest="s1" time="0.0" up/>
<schedule origin="s1" dest="server" time="0.0" up/>
<schedule origin="server" dest="s1" time="0.5" down/>
<schedule origin="s1" dest="server" time="0.5" down/>
<schedule origin="server" dest="s1" time="1.0" up/>
<schedule origin="s1" dest="server" time="1.0" up/>
etc.
```

### Churn

Churn simply describes the crashing of nodes and the joining of identical nodes as a reaction to it. Churn can be applied both in absolute numbers (of instances) as well as percentually, and the scope can be either the name of a service, one or more tags, or nothing (then it is applied to all the services).

```
from 0s to 100s churn 20%
churn backend 3
```

## Ideas

- Join two input graphs, e.g. from two files
- Abort parsing and print message if wrong actions for wrong elements (except if -f flag or similar is set)
- The language should also be able to generate the static part


## Language Definition (dynamic part)

Each line is an `<event sequence>`.

```
<event sequence> := <period event sequence> | <instant event sequence>
<period event sequence> := <interval period event sequence> | <continuous period event sequence>
<interval period event sequence> := <interval> <period event> (and <period event>)*
<continuous period event sequence> := <period event> (and <period event>)*
<interval> := from \ds to \ds

<period event> := <churn event> | <flap event> | <period disconnect event>
<churn event> := churn <selector> <churn args>
<flap event> := flap <selector> <flap args>
<period disconnect event> := disconnect <service identifier> <amount>

<churn args> := \d% | \d
<flap args> := freq \ds

<amount> := \d | ​ɛ
<selector> := <entities> | <tags> | ​ɛ
<entities> := <entity>(;<entity>)*
<tags> := <tag>(;<tag>)*
<entity> := <link identifier> | <bridge identifier> | <service identifier>
<tag> := \w
<link identifier> := \w--\w
<bridge identifier> := \w
<service identifier> := \w

<instant event sequence> := <instant> <instant event> (and <instant event>)*
<instant> := at \ds

<instant event> := <join event> | <crash event> | <set event> | <partition event> | <disconnect event> | <reconnect event> | <quit event>
<join event> := join <service identifier> <amount>
<crash event> := crash <service identifier> <amount>
<set event> := set <selector> (bw=<bandwidth>)? (loss=<<loss>)? (lat=<latency>)? (j=<jitter>)?
<partition event> := partition <partition list>
<disconnect event> := disconnect <service identifier> <amount>
<reconnect event> := reconnect  <service identifier> <amount>
<quit event> := quit

<bandwidth> := \d(​ɛ|K|M|G)bps
<loss> := \d(.\d)?
<latency> := \d
<jitter> := \d(.\d)?

<partition list> := <partition entities>(;<partition entities>)+
<partition entities> := <entity>( <entity>)*

```

&epsilon; means the empty string.
`\d` means any number of digits, and `\w` means any alphanumeric string.

Note that if there is at least one `continuous period event sequence`, there must be exactly one `quit` event.
