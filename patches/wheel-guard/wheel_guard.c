/* wheel-guard: the wheel does nothing when the screen light is off. Refer to re/wheel-guard.md.
 *
 * The firmware turns the screen light off when the time of Settings > Backlight Timer has passed
 * with no use of the iPod. A touch of the wheel in a pocket then changes the volume or the song.
 * This patch ignores the wheel (event type 0xf) from the moment that this time has passed, until
 * a button is pushed (event type 4). The buttons operate as before.
 *
 * Settings > Wheel Guard turns the guard On or Off on the iPod. The value is in the file
 * iPod_Control/iTunes/iPodFirmWheelGuard (one character: 0 or 1). Without the file, the guard is On.
 *
 * The hooks:
 *   0x6701f0: the slot of the UI event handler 0x1d81cc (word, with a chain: Cover Flow uses the
 *             same slot). The UI object has the application object at + 0x18, and the application
 *             object has the Backlight Timer in seconds at + 0x444 (0xffff: Always On, 0: Off,
 *             0xfffe: 10 seconds).
 *   0x21f254: the general lookup (b, with a chain): the text of the label "Wheel Guard".
 *   0x66c94c, 0x66c950: the get and the set method of the settings object (word, with a chain):
 *             the value text On or Off, and the change of the value. The patch.json section
 *             "settings_items" adds the item to the Settings menu after Clicker.
 */

#define USEC_TIMER   (*(volatile unsigned *)0x60005010)   /* the microsecond timer */
#define EV_KEY_DOWN  4
#define EV_WHEEL     0xf
#define UI_APP       0x18                                 /* the application object in the UI object */
#define APP_BACKLIGHT 0x444                               /* the Backlight Timer in the application object */
#define MARGIN_US    1000000u                             /* the screen light can need 1 s more */
#define MAX_SECONDS  3600u

#define TAG_STR      0x53747220u                          /* 'Str ' */
#define TAG_VIEW     0x56696577u                          /* 'View' */
#define OP_TEXT_ID   0x70724944u                          /* 'prID': the ID of the value text */
#define OP_TEXT      0x53747220u                          /* 'Str ': the value text */
#define NOTIFY_BOOL  0x426f6f6cu                          /* 'Bool': the notice after a change */
#define MODE_DATA    0x64617461u                          /* 'data' */
#define TYPE_ITUN    0x6974756eu                          /* 'itun': the file type of the other patch files */
#define KEY          0x7e20u                              /* the item (patch.json: 0x60007e20) */
#define LABEL_ID     0x7e21                               /* "Wheel Guard" */
#define STR_ON       0x602e                               /* "On" (firmware string, in each language) */
#define STR_OFF      0x602f                               /* "Off" */

int ui_next(void *ui, int *ev);                           /* the chain: the next hook, or 0x1d81cc */
const char *str_lookup(void *table, int id);              /* 0x21f418 */
void *str_table(void);                                    /* 0x21f3b8 */
void fw_memset0(void *p, unsigned size);                  /* 0x7ccd0 */
void fw_strcpy(char *dst, const char *src);               /* 0x7cd6c */
int file_open(void *path_record, void *fh, int zero, unsigned mode);       /* 0x8f38c */
int file_open_rw(void *path_record, void *fh, unsigned buffer, unsigned mode); /* 0x8f3f8 */
int file_read(void *fh, unsigned *len, void *buf);        /* 0x8f464 */
int file_write(void *fh, unsigned *len, const void *buf); /* 0x8f6f4 */
int file_close(void *fh);                                 /* 0x8f184 */
void file_create(void *path_record, unsigned type, const char *folder, const char *name); /* 0xe468c */
void lookup_continue(void);                               /* 0x21f258 */
/* Set by the patcher (chain): the previous targets of the hooks. */
void *lookup_next(void *provider, unsigned type, int id);
int get_next(void *self, unsigned op, unsigned key, void *out);
int set_next(void *self, unsigned op, unsigned key, void *value);

static const char label[] = "Wheel Guard";
static const char folder[] = "iPod_Control\\iTunes\\";
static const char name[] = "iPodFirmWheelGuard";

static unsigned last_use;                                 /* the time of the last push or accepted wheel event */
static int started;
static int guard_on = -1;                                 /* -1: the file is not read yet (the guard is On) */

/* ---- The value of the item --------------------------------------------------------------------- */

static void make_path(unsigned *path)
{
    fw_memset0(path, 0x108);
    fw_strcpy((char *)path + 4, folder);
    fw_strcpy((char *)path + 4 + sizeof folder - 1, name);
}

/* Makes the file again and writes the value. */
static void save_value(int value)
{
    unsigned path[0x108 / 4], fh[0x30 / 4], len = 1;
    unsigned char c = (unsigned char)('0' + value);

    file_create(path, TYPE_ITUN, folder, name);
    make_path(path);
    fw_memset0(fh, sizeof fh);
    if (file_open_rw(path, fh, 0x1000, MODE_DATA) == 0) {
        file_write(fh, &len, &c);
        file_close(fh);
    }
}

/* Reads the value. Without the file, the guard is On, and the patch writes the file. */
static int value(void)
{
    if (guard_on < 0) {
        int found = 0;
        unsigned path[0x108 / 4], fh[0x30 / 4], got = 1;
        unsigned char c = 0;

        guard_on = 1;
        make_path(path);
        fw_memset0(fh, sizeof fh);
        if (file_open(path, fh, 0, MODE_DATA) == 0) {
            if (file_read(fh, &got, &c) == 0 && got == 1 && (c == '0' || c == '1')) {
                guard_on = c - '0';
                found = 1;
            }
            file_close(fh);
        }
        if (!found)
            save_value(guard_on);
    }
    return guard_on;
}

/* ---- The guard ----------------------------------------------------------------------------------- */

/* The time of the Backlight Timer in microseconds, or 0 if the light never goes off, or if the
 * setting has a value that this patch does not know. */
static unsigned light_time(void *ui)
{
    char *app = *(char **)((char *)ui + UI_APP);
    unsigned seconds;

    if (!app)
        return 0;
    seconds = *(unsigned *)(app + APP_BACKLIGHT);
    if (seconds == 0xfffe)
        seconds = 10;
    if (seconds == 0 || seconds > MAX_SECONDS)
        return 0;
    return seconds * 1000000u + MARGIN_US;
}

int hook_ui_guard(void *ui, int *ev)
{
    int type = ev[1];
    unsigned now = USEC_TIMER, limit;

    if (!started) {                                       /* the first event: the iPod just started */
        started = 1;
        last_use = now;
    }
    if (type == EV_KEY_DOWN) {
        last_use = now;
    } else if (type == EV_WHEEL) {
        limit = guard_on == 0 ? 0 : light_time(ui);
        if (limit && now - last_use >= limit)
            return 1;                                     /* the light is off: the wheel does nothing */
        last_use = now;
    }
    return ui_next(ui, ev);
}

/* ---- The Settings item --------------------------------------------------------------------------- */

/* The first instruction of the general lookup (0x21f254) is replaced by a branch. If no other patch
 * hooks the lookup, lookup_next is this function: it runs that instruction and continues in the firmware. */
__attribute__((naked)) void *lookup_original(void *provider, unsigned type, int id)
{
    __asm__ volatile("push {r3, r4, r5, r6, r7, lr}\n\tb lookup_continue\n");
}

void *hook_lookup(void *provider, unsigned type, int id)
{
    if (guard_on < 0 && type == TAG_VIEW)       /* the first screen: the file system is ready */
        value();
    if (type == TAG_STR && id == LABEL_ID)
        return (void *)label;
    return lookup_next(provider, type, id);
}

int hook_settings_get(void *self, unsigned op, unsigned key, void *out)
{
    if (key == KEY) {
        short id = value() ? STR_ON : STR_OFF;

        if (op == OP_TEXT_ID) {
            *(short *)((char *)self + 0x88) = id;
            *(void **)out = (char *)self + 0x88;
            return 1;
        }
        if (op == OP_TEXT) {
            *(const char **)out = str_lookup(str_table(), id);
            return 1;
        }
        return 0;
    }
    return get_next(self, op, key, out);
}

/* A selection changes the value from On to Off, or from Off to On. */
int hook_settings_set(void *self, unsigned op, unsigned key, void *new_value)
{
    if (key == KEY) {
        guard_on = !value();
        if (guard_on)
            last_use = USEC_TIMER;                        /* the wheel works for the first Backlight Timer */
        save_value(guard_on);
        (*(void (**)(void *, unsigned, unsigned))(*(char **)self + 0x54))(self, NOTIFY_BOOL, key);
        return 1;
    }
    return set_next(self, op, key, new_value);
}
