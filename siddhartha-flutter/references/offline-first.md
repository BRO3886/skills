# Going offline-first (opt-in upgrade)

> **Gate:** Do not build any of this unless the developer has confirmed the app is offline-first. Ask first. Most apps are not, and this machinery is real, ongoing complexity. The default online slice (`vertical-slice.md`) ships without any of it.

This is a **generic** pattern — it does not assume any specific backend. It needs a backend that can offer (1) a delta/changes endpoint with a cursor, (2) idempotent creates keyed by a client-supplied id, and (3) a version field for conflict detection. Map the generic pieces below onto whatever the API actually exposes.

> drift's API evolves — verify table/DAO/`@DriftDatabase` syntax with context7/web before relying.

## The one principle

**The local database is the source of truth. The network is an optimization.**

- The UI reads from drift (ideally as a stream, so writes rebuild the UI instantly).
- A write hits drift immediately *and* enqueues a pending mutation.
- A background sync engine reconciles drift with the server. The UI never waits on the network.

## Layers added to a feature

```
data/
  <feature>_dao.dart        # drift queries for this entity (watch + write)
  <feature>_repository.dart # now LOCAL-FIRST: reads drift, writes drift + enqueues
core/db/
  database.dart             # @DriftDatabase — entity tables + outbox + sync cursor
  sync/sync_engine.dart     # pull + push loop
```

## drift schema

Three kinds of table: your entities, a mutation **outbox**, and a **sync cursor** per entity.

```dart
import 'package:drift/drift.dart';

class Expenses extends Table {
  TextColumn get id => text()();                 // client-supplied UUID
  TextColumn get description => text()();
  IntColumn get amountPaise => integer()();
  TextColumn get paidBy => text()();
  DateTimeColumn get createdAt => dateTime()();
  IntColumn get version => integer().withDefault(const Constant(0))(); // server version
  BoolColumn get deleted => boolean().withDefault(const Constant(false))(); // tombstone
  @override Set<Column> get primaryKey => {id};
}

class Outbox extends Table {
  IntColumn get seq => integer().autoIncrement()();
  TextColumn get entity => text()();             // 'expense'
  TextColumn get entityId => text()();
  TextColumn get op => text()();                 // 'create' | 'update' | 'delete'
  TextColumn get payload => text()();            // JSON of the change
  IntColumn get baseVersion => integer().nullable()(); // version this change was made against
}

class SyncCursors extends Table {
  TextColumn get entity => text()();
  TextColumn get cursor => text().nullable()();  // opaque server cursor
  @override Set<Column> get primaryKey => {entity};
}

@DriftDatabase(tables: [Expenses, Outbox, SyncCursors])
class AppDatabase extends _$AppDatabase { /* ... */ }
```

## Local-first repository

Reads come from drift (as a stream the ViewModel can watch). Writes are transactional: mutate the entity table **and** append to the outbox in one drift transaction, so a write is never half-recorded.

```dart
Stream<List<Expense>> watch(String groupId) =>
    _dao.watchExpenses(groupId).map((rows) => rows.map(_toDomain).toList());

Future<void> create(Expense e) => _db.transaction(() async {
      await _dao.upsert(e);                                  // UI sees it instantly
      await _outbox.enqueue('expense', e.id, 'create', e.toJson(), baseVersion: 0);
    });
```

A `StreamNotifier` ViewModel (Riverpod) `build()`s by returning that stream, so the UI reacts to local writes with zero network round-trip.

## Sync engine

A single loop, triggered on connectivity-regained / app-resume / a timer.

**Pull:**
1. Read the stored cursor for each entity.
2. Call the delta endpoint with the cursor.
3. Apply changes to drift: upsert rows, mark tombstones `deleted = true`, store the new `version`.
4. Advance and persist the cursor.

**Push:**
1. Read the outbox in `seq` order.
2. For each mutation, call the server. The entity id is the client-supplied UUID, so a retried create is idempotent (no duplicate).
3. Send `baseVersion` for conflict detection (the server's `If-Match`-style check).
4. On success: delete the outbox row, store the server's new `version`.
5. **On version conflict** (server rejects because its version moved): this is the **last-write-wins + surface-conflicts** decision point.

## Conflict resolution: LWW + surface

- The app does **not** silently auto-merge concurrent edits.
- On a version conflict, take the server's current state into drift (last-write-wins for storage consistency) **and** surface the conflict to the user — a banner, a "this changed since you edited it" prompt — so a human resolves intent.
- This is deliberately simple. Full field-level/CRDT auto-merge is out of scope; only adopt it if a feature genuinely has frequent concurrent offline edits to the same record (rare for most apps).

## What stays the same

The presentation layer barely changes — the View still watches one provider and switches `AsyncValue`/stream state. The DTO ↔ domain wall, the sealed `Failure`, and the feature folder shape are identical to the online slice. Offline-first is a **data-layer** change, not a UI rearchitecture.
