const storageKey = 'eliza-gemini-history-v1';
const maxSize = 750_000;
const mounts = new WeakMap();

function readHistory() {
  const raw = window.localStorage.getItem(storageKey) ?? '[]';
  const history = JSON.parse(raw);
  if (!Array.isArray(history) || raw.length > maxSize) throw new Error('Invalid history');
  return history;
}

function apply(command) {
  const history = readHistory();
  const index = history.findIndex(item => item.id === command.conversationId);
  if (command.operation === 'delete') {
    if (index >= 0) history.splice(index, 1);
  } else {
    if ((history[index]?.turns?.length ?? 0) !== command.previousTurns) return 'conflict';
    if (index < 0 && history.length >= 20) return 'full';
    if (index >= 0) history.splice(index, 1);
    history.unshift(command.conversation);
  }
  const serialized = JSON.stringify(history);
  if (serialized.length > maxSize) return 'full';
  window.localStorage.setItem(storageKey, serialized);
  return null;
}

export default function ({ data, parentElement, setStateValue }) {
  const mount = mounts.get(parentElement) ?? {
    commandId: null, error: null, pending: null, lastSnapshot: null,
  };
  mounts.set(parentElement, mount);
  let active = true;
  const publish = () => {
    if (!active) return;
    let snapshot;
    try {
      snapshot = JSON.stringify({
        history: readHistory(), commandId: mount.commandId, error: mount.error,
      });
    } catch {
      snapshot = JSON.stringify({ unavailable: true });
    }
    if (mount.lastSnapshot !== snapshot) {
      mount.lastSnapshot = snapshot;
      setStateValue('snapshot', snapshot);
    }
  };

  const command = data?.command;
  if (command && mount.commandId !== command.id) {
    if (!mount.pending) {
      const write = () => apply(command);
      // Serialize simultaneous changes from multiple tabs when Web Locks is available.
      mount.pending = Promise.resolve().then(() => navigator.locks
        ? navigator.locks.request(storageKey, write)
        : write())
        .then(error => { mount.error = error; })
        .catch(() => { mount.error = 'write'; })
        .finally(() => {
          mount.commandId = command.id;
          mount.pending = null;
        });
    }
    mount.pending.then(publish);
  } else {
    publish();
  }
  const onStorage = event => {
    if (event.key === storageKey || event.key === null) publish();
  };
  window.addEventListener('storage', onStorage);
  return () => {
    active = false;
    window.removeEventListener('storage', onStorage);
  };
}
