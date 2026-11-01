/* Dark Mode On/Off in the Settings menu of RetailOS 1.3 (iPod Video).
 *
 * The build (ipodfw.darkmode / DarkMode.swift) puts these items in the osos image:
 *  - the switch table at dark_table: "IFD2", u32 count N, u32 total size, then N entries. Each entry
 *    has the new bytes of one change of the dark theme, in this form:
 *      varint  zigzag(address - end of the previous entry), the first entry counts from 0
 *      varint  length * 2 + 1 if the bytes are LZ4 blocks, else length * 2
 *      varint  size of the LZ4 block (only if the bytes are an LZ4 block)
 *      bytes   the LZ4 block, or the length bytes themselves
 *    A varint has 7 bits in each byte, low bits first. A byte with bit 7 set has a next byte.
 *  - the Settings menu (Menu 24598) with an item for the key KEY and the label LABEL_ID.
 *
 * RetailOS makes its screens one time, at the start, from the View resources. Thus the patch
 * applies the table at the start, before the first View is read: at the first lookup of a View,
 * it reads iPod_Control\iTunes\iPodFirmDarkMode. If the file contains '1', it applies the table.
 * The patch examines the whole table first, without a write. If the table is not correct, the
 * patch changes nothing and the iPod starts in the light mode. When the owner selects the item,
 * the patch writes the other value, saves the settings of the iPod and restarts it.
 *
 * Hooks:
 *  - the first instruction of the general resource lookup (0x21f254): all resource and string
 *    lookups pass there;
 *  - the "get" and "set" methods of the settings object (vtable 0x66c94c and 0x66c950). */

const char *str_lookup(void *table, int id);                                       /* 0x21f418 */
void *str_table(void);                                                             /* 0x21f3b8 */
int settings_get(void *self, unsigned op, unsigned key, void *out);                /* 0x190b00 */
int settings_set(void *self, unsigned op, unsigned key, void *value);              /* 0x1919d8 */
void fw_memset0(void *p, unsigned size);
void fw_strcpy(char *dst, const char *src);
int file_open(void *path_record, void *fh, int zero, unsigned mode);
int file_open_rw(void *path_record, void *fh, unsigned buffer, unsigned mode);
int file_read(void *fh, unsigned *len, void *buf);
int file_write(void *fh, unsigned *len, const void *buf);
int file_seek(void *fh, int unused, unsigned long long position);
int file_close(void *fh);
void save_all(void *app);                                                          /* 0x1ee8b8 */
void prepare_restart(void);                                                        /* 0x94e08 */
void restart(void);                                                                /* 0x1630 */
extern const unsigned dark_table[];                                                /* set by the build */

#define RAM_END    0x800000u                           /* the end of the osos image in RAM */
#define TAG_VIEW   0x56696577u                         /* 'View' */
#define TAG_STR    0x53747220u                         /* 'Str ' */
#define OP_TEXT_ID 0x70724944u                         /* 'prID': the ID of the value text */
#define OP_TEXT    0x53747220u                         /* 'Str ': the value text */
#define KEY        0x60e0u                             /* the Dark Mode item */
#define LABEL_ID   0x7e00                              /* the label "Dark Mode" */
#define STR_ON     0x602e
#define STR_OFF    0x602f
#define APP        (*(void **)0x1081da18)              /* the application object */
#define FILE_PATH  "iPod_Control\\iTunes\\iPodFirmDarkMode"
#define MODE_DATA  0x64617461u                         /* 'data' */

static const char label[] = "Dark Mode";
static int dark;                                       /* the mode since the start */
static int decided;

/* DECODER BEGIN: the host test (tests/test_darkmode.py) compiles this part with a host compiler. */

/* Reads a varint. Returns 0 if it is not complete or too long. */
static int read_varint(const unsigned char **pp, const unsigned char *end, unsigned *out)
{
    const unsigned char *p = *pp;
    unsigned v = 0, shift = 0;
    for (;;) {
        unsigned char b;
        if (p >= end || shift > 28)
            return 0;
        b = *p++;
        v |= (unsigned)(b & 0x7f) << shift;
        if (!(b & 0x80))
            break;
        shift += 7;
    }
    *pp = p;
    *out = v;
    return 1;
}

/* Decodes one LZ4 block of slen bytes to exactly dlen bytes. If write is 0, it only examines
 * the block. Returns 1 if the block is correct. Each read and each write is inside its range. */
static int lz4_block(const unsigned char *s, unsigned slen, unsigned char *d, unsigned dlen, int write)
{
    const unsigned char *se = s + slen;
    unsigned o = 0, k;
    while (s < se) {
        unsigned token = *s++, lit = token >> 4, mlen = token & 15, off;
        if (lit == 15) {
            unsigned char b;
            do {
                if (s >= se)
                    return 0;
                b = *s++;
                lit += b;
            } while (b == 255);
        }
        if (lit > (unsigned)(se - s) || lit > dlen - o)
            return 0;
        if (write)
            for (k = 0; k < lit; k++)
                d[o + k] = s[k];
        s += lit;
        o += lit;
        if (s == se)
            break;                                      /* the last sequence has only bytes */
        if (se - s < 2)
            return 0;
        off = s[0] | ((unsigned)s[1] << 8);
        s += 2;
        if (off == 0 || off > o)
            return 0;
        if (mlen == 15) {
            unsigned char b;
            do {
                if (s >= se)
                    return 0;
                b = *s++;
                mlen += b;
            } while (b == 255);
        }
        mlen += 4;
        if (mlen > dlen - o)
            return 0;
        if (write)
            for (k = 0; k < mlen; k++)
                d[o + k] = d[o + k - off];
        o += mlen;
    }
    return o == dlen;
}

/* Goes through the table. If write is 0, it only examines the table. Returns 1 if the table is
 * correct. `base` is the address of osos in RAM (0 on the iPod). */
static int walk_table(const unsigned char *t, unsigned long base, int write)
{
    unsigned n, total, i, prev_end = 0;
    const unsigned char *p = t + 12, *end;
    n = t[4] | ((unsigned)t[5] << 8) | ((unsigned)t[6] << 16) | ((unsigned)t[7] << 24);
    total = t[8] | ((unsigned)t[9] << 8) | ((unsigned)t[10] << 16) | ((unsigned)t[11] << 24);
    if (total < 12 || total > RAM_END)
        return 0;
    end = t + total;
    for (i = 0; i < n; i++) {
        unsigned zz, len2, len, size, addr, k;
        unsigned char *d;
        if (!read_varint(&p, end, &zz) || !read_varint(&p, end, &len2))
            return 0;
        len = len2 >> 1;
        size = len;
        if ((len2 & 1) && !read_varint(&p, end, &size))
            return 0;
        addr = prev_end + ((zz >> 1) ^ (0u - (zz & 1)));
        if (size > (unsigned)(end - p) || addr >= RAM_END || len > RAM_END - addr)
            return 0;
        d = (unsigned char *)(base + addr);
        if ((unsigned long)d < (unsigned long)end && (unsigned long)d + len > (unsigned long)t)
            return 0;                                   /* the entry would change the table */
        if (len2 & 1) {
            if (!lz4_block(p, size, d, len, write))
                return 0;
        } else if (write) {
            for (k = 0; k < len; k++)
                d[k] = p[k];
        }
        p += size;
        prev_end = addr + len;
    }
    return p == end;
}

/* DECODER END */

static void apply_table(void)
{
    const unsigned char *t = (const unsigned char *)dark_table;
    if (t[0] != 'I' || t[1] != 'F' || t[2] != 'D' || t[3] != '2')
        return;
    if (walk_table(t, 0, 0))
        walk_table(t, 0, 1);
}

static void make_path(unsigned *path)
{
    fw_memset0(path, 0x108);
    fw_strcpy((char *)path + 4, FILE_PATH);
}

/* Returns 1 if the file contains '1'. No file or an error: 0 (light). */
static int read_setting(void)
{
    unsigned path[0x108 / 4], fh[0x30 / 4], got = 1;
    unsigned char c = 0;
    int err;
    make_path(path);
    fw_memset0(fh, sizeof fh);
    if (file_open(path, fh, 0, MODE_DATA) != 0)
        return 0;
    err = file_read(fh, &got, &c);
    file_close(fh);
    return err == 0 && got == 1 && c == '1';
}

/* Writes '1' or '0' at the start of the file. The file must exist (iPodFirm writes it). */
static int write_setting(int on)
{
    unsigned path[0x108 / 4], fh[0x30 / 4], len = 1;
    unsigned char c = on ? '1' : '0';
    int err, err2;
    make_path(path);
    fw_memset0(fh, sizeof fh);
    err = file_open_rw(path, fh, 0x1000, MODE_DATA);
    if (err != 0)
        return err;
    err = file_seek(fh, 0, 0);
    if (err == 0)
        err = file_write(fh, &len, &c);
    err2 = file_close(fh);
    return err != 0 ? err : err2;
}

/* The first instruction of the general lookup (0x21f254) is replaced by a branch to
 * hook_lookup. This function runs that instruction and continues in the firmware function. */
__attribute__((naked)) void *lookup_original(void *provider, unsigned type, int id)
{
    __asm__ volatile("push {r3, r4, r5, r6, r7, lr}\n\tb lookup_continue\n");
}

void *hook_lookup(void *provider, unsigned type, int id)
{
    if (!decided && type == TAG_VIEW) {
        decided = 1;
        dark = read_setting();
        if (dark)
            apply_table();
    }
    if (type == TAG_STR && id == LABEL_ID)
        return (void *)label;
    return lookup_original(provider, type, id);
}

int hook_settings_get(void *self, unsigned op, unsigned key, void *out)
{
    if (key == KEY) {
        short value = dark ? STR_ON : STR_OFF;
        if (op == OP_TEXT_ID) {
            *(short *)((char *)self + 0x88) = value;
            *(void **)out = (char *)self + 0x88;
            return 1;
        }
        if (op == OP_TEXT) {
            *(const char **)out = str_lookup(str_table(), value);
            return 1;
        }
        return 0;
    }
    return settings_get(self, op, key, out);
}

int hook_settings_set(void *self, unsigned op, unsigned key, void *value)
{
    if (key == KEY) {
        if (write_setting(!dark) == 0) {
            if (APP)
                save_all(APP);              /* the settings of the iPod, as before a sleep */
            prepare_restart();
            restart();
        }
        return 1;
    }
    return settings_set(self, op, key, value);
}
