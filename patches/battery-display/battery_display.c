/* battery-display: a battery percentage inside the battery icon. Refer to re/battery.md.
 *
 * Options in patch.json:
 *   display_mode: 0 icon, 1 icon with the percentage inside it.
 *   battery_data: 0 Apple (the icon value x 5), 1 custom battery (the table below).
 *   smoothing: 1 uses a longer average and stops small rises of the percentage. It also gives Apple
 *   data steps of 1 %, with a line between the limits of the firmware table.
 *
 * The text style and the box of the text are in the data of the two battery Views (25598 and 25599).
 * The "bytes" in patch.json give the text Type 24171 (Pixo 7, bold, centred, black), and a box that is
 * inside the body of the icon (2 pixels from the left, 5 from the tip, 1 from the top, 3 from the bottom). A style that the code set at run time did not stay on the real iPod
 * (version 0.3), so the style is in the data. Use only a font and a size that the firmware has:
 * version 0.5 used Podium Sans 9, and the iPod restarted at the Apple logo.
 *
 * The hooks:
 *   0xb4abc:  after the read of the switch files, sets the byte of _show_voltage. The firmware then
 *             shows and refreshes the text child of the battery view.
 *   0x1e8af8: in case 0x63fc, gives the text of the percentage in place of the raw value.
 *   0x1ae838: the only icon call for the battery picture. Other callers keep the Apple value, so the
 *             low battery behaviour does not change.
 *   0x1ae6b8: the firmware shows the text child only. Below 100 % the hook also shows the icon child,
 *             under the text. At 100 % it shows only the icon. A charge takes the other path in 0x1ae774,
 *             so the charge pictures stay with no text.
 */

#define USEC         (*(volatile unsigned *)0x60005010)   /* the microsecond timer */
#define SHOW_VOLTAGE (*(volatile char *)0x1081dfe3)       /* the byte of _show_voltage */
#define READ_US      30000000u                            /* the shortest time between raw reads */
#define AVERAGE      8
#define LONG_AVERAGE 32
#define RISE_PERCENT 5                                    /* a smaller rise does not show */
#define LIMITS       15                                   /* the limits of a firmware battery table */
#define VIEW_FLAGS   0x20
#define VIEW_SMALL   0x1000000u                           /* a view with fewer pictures */
#define VIEW_LIST    0x78
#define VIEW_SHOW    0x9c                                 /* the vtable offset of the show method */
#define TEXT_CHILD   0x1b
#define NO_CHILD     0x1c
#define SMALL_TEXT   0x17
#define SMALL_ICON   4
#define ICON_FIRST   4                                    /* the child of the icon value 0 */
#define FULL_PERCENT 100                                  /* at this value only the icon shows */

void read_switches(void *a);
unsigned hardware_revision(void);
int battery_icon(void *provider, int mode);
int battery_raw(void);
void show_child(void *view, int index);
void child_first(void *walk, void *list, int from);
int child_next(void *walk, void **child);
void child_end(void *walk);

unsigned display_mode = 1;                                /* an option in patch.json */
unsigned battery_data = 0;                                /* an option in patch.json */
unsigned smoothing = 0;                                   /* an option in patch.json */

/* Provisional: the second log of the owner's larger battery, with 20.3 hours from raw 438. The app
 * writes a curve from an imported log over these values. The raw values decrease. */
#define CURVE_POINTS 16u
unsigned short curve_raw[CURVE_POINTS] = { 438, 423, 415, 405, 380, 363, 350, 337, 325, 311, 300, 284, 250, 200, 150, 116 };
unsigned short curve_pct[CURVE_POINTS] = { 100,  89,  83,  77,  68,  61,  55,  50,  43,  37,  34,  31,  24,  12,   4,   0 };

/* The icon value of each level of a firmware battery table (0x1dfe44: level x 20 / 15). */
static const unsigned char level_icon[LIMITS + 1] = { 0, 1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15, 17, 18, 20 };

static unsigned samples[LONG_AVERAGE], sample_count, sample_next, sample_sum;
static unsigned last_read;
static int last_percent = -1;
static int last_icon = -1;
static char text[5];

/* The average of the last raw values, or 0 if the iPod has no value yet. */
static unsigned mean_raw(void)
{
    unsigned now = USEC, size = smoothing ? LONG_AVERAGE : AVERAGE;

    if (!sample_count || now - last_read >= READ_US) {
        int raw = battery_raw();
        last_read = now;
        if (raw > 0 && raw < 1024) {
            if (sample_count == size)
                sample_sum -= samples[sample_next];
            else
                sample_count++;
            samples[sample_next] = raw;
            sample_sum += raw;
            sample_next = sample_next + 1 == size ? 0 : sample_next + 1;
        }
    }
    return sample_count ? sample_sum / sample_count : 0;
}

static int custom_percent(unsigned mean)
{
    unsigned i, span;

    if (mean >= curve_raw[0])
        return 100;
    for (i = 1; i < CURVE_POINTS; i++) {
        if (mean >= curve_raw[i]) {
            span = curve_raw[i - 1] - curve_raw[i];
            return curve_pct[i] + (mean - curve_raw[i]) * (curve_pct[i - 1] - curve_pct[i]) / span;
        }
    }
    return 0;
}

/* The limits that 0x264ee8 selects from the hardware revision. */
static const unsigned short *apple_limits(void)
{
    switch (hardware_revision() >> 16) {
    case 4: case 5: return (const unsigned short *)0x1081de98;
    case 7:         return (const unsigned short *)0x1081ded4;
    case 9:         return (const unsigned short *)0x1081def2;
    case 0xb:       return (const unsigned short *)0x1081df10;
    case 0xc:       return (const unsigned short *)0x1081df2e;
    default:        return (const unsigned short *)0x1081deb6;
    }
}

/* A line between the limits. Each limit is one level of 15, as in 0x1dfe44. */
static int apple_percent(unsigned mean)
{
    const unsigned short *limit = apple_limits();
    unsigned i;

    if (mean < limit[0])
        return 0;
    for (i = 1; i < LIMITS; i++)
        if (mean < limit[i])
            return (i * 100 + (mean - limit[i - 1]) * 100 / (limit[i] - limit[i - 1])) / LIMITS;
    return 100;
}

/* The percentage. It also keeps the icon value in last_icon. Apple data asks the firmware one time
 * for each call, because the firmware lets the icon fall only one step for each call. */
static int percent(void *provider)
{
    int value, icon = -1;

    if (!battery_data) {
        icon = battery_icon(provider, 0);
        if (icon < 0 || icon > 20)                        /* 21: no value yet */
            icon = -1;
    }
    if (battery_data || smoothing) {
        unsigned mean = mean_raw();
        if (!mean)
            return last_percent < 0 ? 0 : last_percent;
        value = battery_data ? custom_percent(mean) : apple_percent(mean);
        if (smoothing && last_percent >= 0 && value > last_percent && value < last_percent + RISE_PERCENT)
            value = last_percent;
    } else {
        if (icon < 0)
            return last_percent < 0 ? 0 : last_percent;
        value = icon * 5;
    }
    last_percent = value;
    if (battery_data)
        last_icon = value / 5;
    else if (icon >= 0)
        last_icon = icon;
    return value;
}

/* The text of the percentage, with no "%" sign. The firmware gives it to sprintf with "%s". */
const char *battery_text(void *provider)
{
    unsigned value = percent(provider), n = 0;

    if (value >= 100)
        text[n++] = '0' + value / 100;
    if (value >= 10)
        text[n++] = '0' + value / 10 % 10;
    text[n++] = '0' + value % 10;
    text[n] = 0;
    return text;
}

const char *text_format(void)
{
    return "%s";
}

/* In place of "adr r1, %ld" at 0x1e8af8. r5 is the provider. r2 is the raw value. The next
 * instructions set r0 and call sprintf with r1 and r2. */
__attribute__((naked)) void hook_text(void)
{
    __asm__ volatile(
        "push  {r4, lr}\n"
        "mov   r0, r5\n"
        "bl    battery_text\n"
        "mov   r4, r0\n"
        "bl    text_format\n"
        "mov   r1, r0\n"
        "mov   r2, r4\n"
        "pop   {r4, pc}\n");
}

/* Replaces the call of 0x1d3ac4. That function clears the byte, so set the byte after it. */
void hook_switches(void *a)
{
    read_switches(a);
    if (display_mode)
        SHOW_VOLTAGE = 1;
}

/* The icon value of the battery picture. */
int hook_icon(void *provider, int mode)
{
    int value = battery_icon(provider, mode);

    return battery_data ? percent(provider) / 5 : value;
}

/* The icon value before the text has given one: the level of the raw value, as the firmware sees it,
 * or the custom curve. -1 if the iPod has no value yet. */
static int first_icon(void)
{
    if (battery_data) {
        unsigned mean = mean_raw();
        return mean ? custom_percent(mean) / 5 : -1;
    } else {
        const unsigned short *limit = apple_limits();
        int raw = battery_raw();
        unsigned level = 0;

        if (raw <= 0 || raw >= 1024)
            return -1;
        while (level < LIMITS && (unsigned)raw >= limit[level])
            level++;
        return level_icon[level];
    }
}

/* The percentage now: the last text, or an estimate from the raw value. -1 if the iPod has no value. */
static int shown_percent(void)
{
    int icon;

    if (last_percent >= 0)
        return last_percent;
    if (battery_data) {
        unsigned mean = mean_raw();
        return mean ? custom_percent(mean) : -1;
    }
    icon = first_icon();
    return icon < 0 ? -1 : icon * 5;
}

/* Replaces the call of 0x1ae6d0 (view, index). The firmware selects the text child when the switch
 * is on. Below 100 %, this hook shows the text child and also the icon child. The icon is drawn
 * first, so the text is on top of it. At 100 %, it shows only the Apple picture of a full battery.
 * A charge picture, or a view with no text, goes through with no change. */
void hook_show(void *view, int index)
{
    unsigned char walk[20];
    void *child;
    int small, second, icon, i = 0;

    if (!display_mode || index >= NO_CHILD) {
        show_child(view, index);
        return;
    }
    small = (*(unsigned *)((char *)view + VIEW_FLAGS) & VIEW_SMALL) != 0;
    if (index != (small ? SMALL_TEXT : TEXT_CHILD)) {
        show_child(view, index);
        return;
    }
    if (small) {
        show_child(view, index);
        second = SMALL_ICON;
    } else {
        icon = last_icon >= 0 ? last_icon : first_icon();
        if (icon >= 0 && shown_percent() >= FULL_PERCENT) {
            show_child(view, ICON_FIRST + icon);
            return;
        }
        show_child(view, index);
        if (icon < 0)
            return;
        second = icon + ICON_FIRST;
    }
    child_first(walk, (char *)view + VIEW_LIST, -2);
    while (child_next(walk, &child)) {
        if (i == second)
            (*(void (**)(void *, int))(*(char **)child + VIEW_SHOW))(child, 1);
        i++;
    }
    child_end(walk);
}
