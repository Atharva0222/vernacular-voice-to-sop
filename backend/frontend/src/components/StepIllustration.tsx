import type { Step } from '../lib/types'

/** Demo-only hand-made illustrations, keyed by the same `step.icon` keyword `iconFor()` (see
 * `lib/icons.ts`) maps to a small Lucide glyph. Covers the keywords actually used by the three
 * seeded SOPs (Press 1, Press 2, drill b) - not a general mapping for arbitrary future icons.
 * New SOPs get theirs added here by hand until/unless this becomes a real generation pipeline.
 *
 * Style: static, monochrome line-art - like an IKEA assembly manual, not a colored cartoon and
 * not animated. Bold black outlines, arrows for direction/motion, a plain hand silhouette doing
 * the action. A worker should understand the action from the picture alone in one glance; text
 * underneath is there to confirm, not to carry the meaning. */

type Props = Pick<Step, 'icon' | 'is_safety_warning'> & { image_url?: string | null }

const INK = '#1e293b'
const DANGER = '#dc2626'
const BG = '#f8fafc'
const W = 4

/** A plain outlined hand + forearm, the one reused "character" across every scene. */
function Hand({ x, y, rotate = 0, flip = false }: { x: number; y: number; rotate?: number; flip?: boolean }) {
  return (
    <g
      transform={`translate(${x} ${y}) rotate(${rotate}) scale(${flip ? -1 : 1} 1)`}
      fill="#fff"
      stroke={INK}
      strokeWidth={W}
      strokeLinejoin="round"
    >
      <rect x="-14" y="18" width="28" height="48" rx="12" />
      <line x1="-14" y1="32" x2="14" y2="32" strokeWidth="3" />
      <rect x="-20" y="-20" width="40" height="40" rx="16" />
      <rect x="4" y="-6" width="20" height="26" rx="10" transform="rotate(30 4 -6)" />
    </g>
  )
}

/** A straight arrow from (x1,y1) to (x2,y2). */
function Arrow({ x1, y1, x2, y2 }: { x1: number; y1: number; x2: number; y2: number }) {
  const angle = (Math.atan2(y2 - y1, x2 - x1) * 180) / Math.PI
  return (
    <g>
      <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={INK} strokeWidth={5} strokeLinecap="round" />
      <polygon points="0,-8 16,0 0,8" fill={INK} transform={`translate(${x2} ${y2}) rotate(${angle})`} />
    </g>
  )
}

/** A curved arrow sweeping around a pivot, for "turn this" actions. */
function CurveArrow({ cx, cy, r, from, to }: { cx: number; cy: number; r: number; from: number; to: number }) {
  const rad = (d: number) => (d * Math.PI) / 180
  const sx = cx + r * Math.cos(rad(from))
  const sy = cy + r * Math.sin(rad(from))
  const ex = cx + r * Math.cos(rad(to))
  const ey = cy + r * Math.sin(rad(to))
  const large = Math.abs(to - from) > 180 ? 1 : 0
  const tangent = to + 90
  return (
    <g>
      <path d={`M${sx} ${sy} A${r} ${r} 0 ${large} 1 ${ex} ${ey}`} fill="none" stroke={INK} strokeWidth={5} strokeLinecap="round" />
      <polygon points="0,-8 16,0 0,8" fill={INK} transform={`translate(${ex} ${ey}) rotate(${tangent})`} />
    </g>
  )
}

function Scene({ children, wide = false }: { children: React.ReactNode; wide?: boolean }) {
  return (
    <div style={{ background: BG, width: '100%', aspectRatio: wide ? '12 / 5' : '6 / 5' }}>
      <svg viewBox={wide ? '0 0 480 200' : '0 0 240 200'} width="100%" height="100%" preserveAspectRatio="xMidYMid meet" role="img" aria-hidden="true">
        {children}
      </svg>
    </div>
  )
}

const PowerOff = () => (
  <Scene>
    <rect x="80" y="40" width="60" height="110" rx="10" fill="#fff" stroke={INK} strokeWidth={W} />
    <rect x="98" y="100" width="24" height="42" rx="6" fill={INK} />
    <text x="110" y="166" fontSize="18" fontWeight="700" fill={INK} textAnchor="middle">
      OFF
    </text>
    <Hand x={178} y={100} rotate={-15} />
    <Arrow x1={178} y1={70} x2={178} y2={92} />
  </Scene>
)

const PowerOn = () => (
  <Scene>
    <rect x="80" y="40" width="60" height="110" rx="10" fill="#fff" stroke={INK} strokeWidth={W} />
    <rect x="98" y="48" width="24" height="42" rx="6" fill={INK} />
    <text x="110" y="166" fontSize="18" fontWeight="700" fill={INK} textAnchor="middle">
      ON
    </text>
    <Hand x={178} y={90} rotate={15} />
    <Arrow x1={178} y1={120} x2={178} y2={98} />
  </Scene>
)

const Check = () => (
  <Scene>
    <rect x="60" y="34" width="90" height="120" rx="10" fill="#fff" stroke={INK} strokeWidth={W} />
    <rect x="82" y="26" width="46" height="16" rx="6" fill="#fff" stroke={INK} strokeWidth={W} />
    <line x1="76" y1="74" x2="134" y2="74" stroke={INK} strokeWidth="3" />
    <line x1="76" y1="96" x2="134" y2="96" stroke={INK} strokeWidth="3" />
    <path d="M74 118 L92 136 L136 92" fill="none" stroke={INK} strokeWidth="9" strokeLinecap="round" strokeLinejoin="round" />
    <Hand x={178} y={110} rotate={-20} />
  </Scene>
)

const Tighten = () => (
  <Scene>
    <rect x="30" y="130" width="150" height="40" rx="8" fill="#fff" stroke={INK} strokeWidth={W} />
    <polygon points="105,112 120,120 120,136 105,144 90,136 90,120" fill="#fff" stroke={INK} strokeWidth={W} strokeLinejoin="round" />
    <rect x="97" y="18" width="16" height="76" rx="7" fill="#fff" stroke={INK} strokeWidth={W} />
    <rect x="88" y="92" width="34" height="30" rx="10" fill="#fff" stroke={INK} strokeWidth={W} />
    <CurveArrow cx={105} cy={128} r={28} from={-150} to={50} />
    <Hand x={105} y={34} rotate={180} />
  </Scene>
)

const Ppe = () => (
  <Scene>
    <circle cx="120" cy="118" r="28" fill="#fff" stroke={INK} strokeWidth={W} />
    <path d="M82 100 a38 38 0 0 1 76 0 Z" fill="#fff" stroke={INK} strokeWidth={W} strokeLinejoin="round" />
    <ellipse cx="120" cy="100" rx="46" ry="9" fill="#fff" stroke={INK} strokeWidth={W} />
    <Arrow x1={120} y1={28} x2={120} y2={54} />
  </Scene>
)

const Clean = () => (
  <Scene>
    <rect x="30" y="156" width="150" height="8" rx="3" fill={INK} />
    <line x1="176" y1="38" x2="110" y2="128" stroke={INK} strokeWidth="9" strokeLinecap="round" />
    <polygon points="176,38 204,54 182,80 154,64" fill="#fff" stroke={INK} strokeWidth={W} strokeLinejoin="round" />
    {[
      [60, 56],
      [90, 96],
      [44, 100],
    ].map(([x, y], i) => (
      <path
        key={i}
        d={`M${x} ${y - 9} L${x + 3} ${y - 3} L${x + 9} ${y} L${x + 3} ${y + 3} L${x} ${y + 9} L${x - 3} ${y + 3} L${x - 9} ${y} L${x - 3} ${y - 3} Z`}
        fill="none"
        stroke={INK}
        strokeWidth="3"
      />
    ))}
    <Hand x={110} y={128} rotate={125} />
  </Scene>
)

const WearGloves = () => (
  <Scene>
    <path
      d="M50 160 V92 q0-11 11-11 11 0 11 11 v10 q0-11 11-11 11 0 11 11 v6 q0-11 11-11 11 0 11 11 v52 q0 14-14 14 H66 q-16 0-16-18 Z"
      fill="#fff"
      stroke={INK}
      strokeWidth={W}
      strokeLinejoin="round"
    />
    <line x1="50" y1="112" x2="106" y2="112" stroke={INK} strokeWidth="3" />
    <Hand x={78} y={40} rotate={0} />
    <Arrow x1={78} y1={64} x2={78} y2={86} />
  </Scene>
)

const Inspect = () => (
  <Scene>
    <rect x="40" y="94" width="96" height="54" rx="8" fill="#fff" stroke={INK} strokeWidth={W} />
    <circle cx="88" cy="121" r="20" fill="#fff" stroke={INK} strokeWidth={W} />
    <line x1="88" y1="121" x2="88" y2="106" stroke={INK} strokeWidth="3" strokeLinecap="round" />
    <line x1="88" y1="121" x2="98" y2="126" stroke={INK} strokeWidth="3" strokeLinecap="round" />
    <circle cx="160" cy="70" r="26" fill="none" stroke={INK} strokeWidth={W} />
    <line x1="179" y1="89" x2="200" y2="110" stroke={INK} strokeWidth={6} strokeLinecap="round" />
    <Hand x={160} y={140} rotate={0} />
  </Scene>
)

const Measure = () => (
  <Scene>
    <rect x="30" y="82" width="160" height="26" rx="4" fill="#fff" stroke={INK} strokeWidth={W} />
    {Array.from({ length: 13 }).map((_, i) => (
      <line key={i} x1={40 + i * 12} y1="82" x2={40 + i * 12} y2={i % 2 === 0 ? 98 : 92} stroke={INK} strokeWidth="2" />
    ))}
    <rect x="124" y="70" width="12" height="46" rx="3" fill="#fff" stroke={INK} strokeWidth={W} />
    <Arrow x1={96} y1={56} x2={122} y2={74} />
    <Hand x={130} y={146} rotate={0} />
  </Scene>
)

const KeepHandsAway = () => (
  <Scene>
    <g transform="translate(166 86)">
      {Array.from({ length: 6 }).map((_, i) => (
        <rect key={i} x="-5" y="-38" width="10" height="16" rx="3" fill="#fff" stroke={INK} strokeWidth="2.5" transform={`rotate(${i * 60})`} />
      ))}
      <circle r="20" fill="#fff" stroke={INK} strokeWidth={W} />
    </g>
    <Hand x={66} y={112} rotate={-8} />
    <circle cx="66" cy="112" r="40" fill="none" stroke={DANGER} strokeWidth="7" />
    <line x1="38" y1="84" x2="94" y2="140" stroke={DANGER} strokeWidth="7" />
    <Arrow x1={110} y1={100} x2={86} y2={108} />
  </Scene>
)

const PlaceConveyor = () => (
  <Scene>
    <rect x="20" y="130" width="200" height="12" rx="5" fill="#fff" stroke={INK} strokeWidth={W} />
    {Array.from({ length: 7 }).map((_, i) => (
      <line key={i} x1={32 + i * 28} y1="130" x2={22 + i * 28} y2="142" stroke={INK} strokeWidth="2.5" />
    ))}
    <rect x="58" y="86" width="48" height="40" rx="4" fill="#fff" stroke={INK} strokeWidth={W} />
    <Arrow x1={210} y1={136} x2={230} y2={136} />
    <Hand x={40} y={54} rotate={25} />
    <Arrow x1={52} y1={66} x2={72} y2={82} />
  </Scene>
)

const PressButton = () => (
  <Scene>
    <rect x="50" y="76" width="140" height="66" rx="10" fill="#fff" stroke={INK} strokeWidth={W} />
    <circle cx="120" cy="109" r="28" fill="#fff" stroke={INK} strokeWidth={W} />
    <circle cx="120" cy="109" r="17" fill={INK} />
    <Hand x={120} y={46} rotate={0} />
    <Arrow x1={120} y1={68} x2={120} y2={78} />
  </Scene>
)

const StackBox = () => (
  <Scene>
    <rect x="48" y="112" width="60" height="40" rx="4" fill="#fff" stroke={INK} strokeWidth={W} />
    <rect x="112" y="112" width="60" height="40" rx="4" fill="#fff" stroke={INK} strokeWidth={W} />
    <rect x="80" y="50" width="60" height="40" rx="4" fill="#fff" stroke={INK} strokeWidth={W} />
    <Arrow x1={110} y1={96} x2={110} y2={108} />
    <Hand x={178} y={50} rotate={10} />
  </Scene>
)

const Fallback = ({ isSafety }: { isSafety: boolean }) => (
  <Scene>
    {isSafety ? (
      <polygon points="120,44 170,144 70,144" fill="#fff" stroke={DANGER} strokeWidth={7} strokeLinejoin="round" />
    ) : (
      <circle cx="120" cy="100" r="44" fill="#fff" stroke={INK} strokeWidth={W} />
    )}
    <Hand x={120} y={100} rotate={-10} />
  </Scene>
)

/** A real (AI-generated, user-supplied) illustration image, same frame/background as the
 * hand-drawn Scene so it sits consistently among the SVG ones in the modal. */
function ImageScene({ src }: { src: string }) {
  return (
    <div style={{ background: BG, width: '100%', aspectRatio: '6 / 5' }}>
      <img src={src} alt="" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
    </div>
  )
}

const ASSET_BASE = `${import.meta.env.BASE_URL}illustrations/`
const PickNeedle = () => <ImageScene src={`${ASSET_BASE}pick_needle.png`} />
const InsertNeedle = () => <ImageScene src={`${ASSET_BASE}insert_needle.png`} />
const NeedleOrient = () => <ImageScene src={`${ASSET_BASE}needle_orient.png`} />
const TightenClamp = () => <ImageScene src={`${ASSET_BASE}tighten_clamp.png`} />
const NeedleCheck = () => <ImageScene src={`${ASSET_BASE}needle_check.png`} />
const CheckFanParts = () => <ImageScene src={`${ASSET_BASE}check_fan_parts.png`} />
const MountHub = () => <ImageScene src={`${ASSET_BASE}mount_hub.png`} />
const InsertBlade = () => <ImageScene src={`${ASSET_BASE}insert_blade.png`} />
const CrisscrossTighten = () => <ImageScene src={`${ASSET_BASE}crisscross_tighten.png`} />
const SpinCheck = () => <ImageScene src={`${ASSET_BASE}spin_check.png`} />
const FanGuard = () => <ImageScene src={`${ASSET_BASE}fan_guard.png`} />
const FanFinalCheck = () => <ImageScene src={`${ASSET_BASE}fan_final_check.png`} />

const ILLUSTRATION_MAP: Record<string, () => React.JSX.Element> = {
  power_off: PowerOff,
  power_on: PowerOn,
  check: Check,
  moving_parts: Tighten,
  ppe: Ppe,
  clean: Clean,
  wear_gloves: WearGloves,
  inspect: Inspect,
  measure: Measure,
  keep_hands_away: KeepHandsAway,
  hands_away: KeepHandsAway,
  place_conveyor: PlaceConveyor,
  press_button: PressButton,
  stack_box: StackBox,
  stack: StackBox,
  pick_needle: PickNeedle,
  insert_needle: InsertNeedle,
  needle_orient: NeedleOrient,
  tighten_clamp: TightenClamp,
  needle_check: NeedleCheck,
  check_fan_parts: CheckFanParts,
  mount_hub: MountHub,
  insert_blade: InsertBlade,
  crisscross_tighten: CrisscrossTighten,
  spin_check: SpinCheck,
  fan_guard: FanGuard,
  fan_final_check: FanFinalCheck,
}

export function hasIllustration(icon: string): boolean {
  return Boolean(ILLUSTRATION_MAP[(icon || '').trim().toLowerCase()])
}

/** The artwork only - callers decide where/when to show it (see IllustrationModal). A
 * supervisor-uploaded photo (image_url) always wins over the keyword-mapped stock art, since
 * it's a real picture of this specific step rather than a generic stand-in. */
export function StepIllustrationArt({ icon, is_safety_warning, image_url }: Props) {
  if (image_url) return <ImageScene src={image_url} />
  const key = (icon || '').trim().toLowerCase()
  const Illustration = ILLUSTRATION_MAP[key]
  return Illustration ? <Illustration /> : <Fallback isSafety={is_safety_warning} />
}
