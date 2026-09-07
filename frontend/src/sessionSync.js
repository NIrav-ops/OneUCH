const SESSION_EVENT_CHANNEL =
  "oneuch-browser-session";

const SESSION_EVENT_STORAGE_KEY =
  "oneuch_session_event";

const SESSION_ROTATION_LOCK_NAME =
  "oneuch-browser-session-rotation";

const SESSION_ROTATION_STORAGE_KEY =
  "oneuch_session_rotation_lock";

const STORAGE_LOCK_LEASE_MS =
  30000;

const STORAGE_LOCK_WAIT_MS =
  50;

const STORAGE_LOCK_TIMEOUT_MS =
  35000;


function randomOwnerId() {

  if (
    typeof window !== "undefined"
    && window.crypto?.randomUUID
  ) {

    return window.crypto.randomUUID();

  }


  return (
    String(Date.now())
    + "-"
    + Math.random().toString(16).slice(2)
  );

}


const TAB_ID =
  randomOwnerId();


function sleep(
  milliseconds
) {

  return new Promise(
    (resolve) => {

      window.setTimeout(
        resolve,
        milliseconds
      );

    }
  );

}


function parseStoredValue(
  value
) {

  try {

    return JSON.parse(
      value
    );

  } catch {

    return null;

  }

}


function readStorageLock() {

  try {

    return parseStoredValue(
      window.localStorage.getItem(
        SESSION_ROTATION_STORAGE_KEY
      )
    );

  } catch {

    return null;

  }

}


function releaseStorageLock(
  owner
) {

  const current =
    readStorageLock();


  if (
    current?.owner !== owner
  ) {

    return;

  }


  try {

    window.localStorage.removeItem(
      SESSION_ROTATION_STORAGE_KEY
    );

  } catch {

    // Non-secret coordination fallback only.

  }

}


async function withStorageRotationLock(
  callback
) {

  const owner =
    randomOwnerId();

  const deadline =
    Date.now()
    + STORAGE_LOCK_TIMEOUT_MS;


  try {

    window.localStorage.getItem(
      SESSION_ROTATION_STORAGE_KEY
    );

  } catch {

    return callback();

  }


  while (
    Date.now() < deadline
  ) {

    const now =
      Date.now();

    const current =
      readStorageLock();


    if (
      !current
      || Number(
        current.expiresAt || 0
      ) <= now
    ) {

      try {

        window.localStorage.setItem(
          SESSION_ROTATION_STORAGE_KEY,
          JSON.stringify({
            owner,
            expiresAt:
              now
              + STORAGE_LOCK_LEASE_MS,
          })
        );

      } catch {

        return callback();

      }


      await sleep(
        15
      );


      const confirmed =
        readStorageLock();


      if (
        confirmed?.owner === owner
      ) {

        const heartbeat =
          window.setInterval(
            () => {

              const held =
                readStorageLock();


              if (
                held?.owner !== owner
              ) {

                return;

              }


              try {

                window.localStorage.setItem(
                  SESSION_ROTATION_STORAGE_KEY,
                  JSON.stringify({
                    owner,
                    expiresAt:
                      Date.now()
                      + STORAGE_LOCK_LEASE_MS,
                  })
                );

              } catch {

                // Keep the acquired operation running.

              }

            },
            5000
          );


        try {

          return await callback();

        } finally {

          window.clearInterval(
            heartbeat
          );

          releaseStorageLock(
            owner
          );

        }

      }

    }


    await sleep(
      STORAGE_LOCK_WAIT_MS
    );

  }


  throw new Error(
    "Unable to coordinate the One UCH browser session."
  );

}


export async function withBrowserSessionRotationLock(
  callback
) {

  if (
    typeof callback !== "function"
  ) {

    throw new Error(
      "Browser session callback is unavailable."
    );

  }


  if (
    typeof navigator !== "undefined"
    && navigator.locks?.request
  ) {

    return navigator.locks.request(
      SESSION_ROTATION_LOCK_NAME,
      {
        mode:
          "exclusive",
      },
      callback
    );

  }


  return withStorageRotationLock(
    callback
  );

}


export function publishSessionInvalidation(
  reason = "session-invalidated"
) {

  const event = {
    type:
      "session-invalidated",

    reason:
      String(
        reason
        || "session-invalidated"
      ),

    source:
      TAB_ID,

    createdAt:
      Date.now(),

    nonce:
      randomOwnerId(),
  };


  if (
    typeof BroadcastChannel !==
    "undefined"
  ) {

    const channel =
      new BroadcastChannel(
        SESSION_EVENT_CHANNEL
      );

    channel.postMessage(
      event
    );

    channel.close();

  }


  try {

    window.localStorage.setItem(
      SESSION_EVENT_STORAGE_KEY,
      JSON.stringify(
        event
      )
    );

    window.localStorage.removeItem(
      SESSION_EVENT_STORAGE_KEY
    );

  } catch {

    // BroadcastChannel remains the primary path.

  }


  return event;

}


export function subscribeSessionInvalidation(
  listener
) {

  if (
    typeof listener !== "function"
  ) {

    throw new Error(
      "Session invalidation listener is unavailable."
    );

  }


  const deliver =
    (event) => {

      if (
        event?.type !==
          "session-invalidated"
        ||
        event.source === TAB_ID
      ) {

        return;

      }


      listener(
        event
      );

    };


  let channel =
    null;


  if (
    typeof BroadcastChannel !==
    "undefined"
  ) {

    channel =
      new BroadcastChannel(
        SESSION_EVENT_CHANNEL
      );

    channel.onmessage =
      (message) => {

        deliver(
          message.data
        );

      };

  }


  const storageListener =
    (event) => {

      if (
        event.key !==
          SESSION_EVENT_STORAGE_KEY
        ||
        !event.newValue
      ) {

        return;

      }


      deliver(
        parseStoredValue(
          event.newValue
        )
      );

    };


  window.addEventListener(
    "storage",
    storageListener
  );


  return () => {

    window.removeEventListener(
      "storage",
      storageListener
    );


    if (channel) {

      channel.close();

    }

  };

}
