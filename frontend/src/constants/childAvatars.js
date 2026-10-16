import avatar01 from '../static/avatars/children/avatar_01.png'
import avatar02 from '../static/avatars/children/avatar_02.png'
import avatar03 from '../static/avatars/children/avatar_03.png'
import avatar04 from '../static/avatars/children/avatar_04.png'
import avatar05 from '../static/avatars/children/avatar_05.png'
import avatar06 from '../static/avatars/children/avatar_06.png'

export const CHILD_AVATARS = Object.freeze([
  Object.freeze({ key: 'avatar_01', label: '狐狸', src: avatar01 }),
  Object.freeze({ key: 'avatar_02', label: '兔子', src: avatar02 }),
  Object.freeze({ key: 'avatar_03', label: '小熊猫', src: avatar03 }),
  Object.freeze({ key: 'avatar_04', label: '熊', src: avatar04 }),
  Object.freeze({ key: 'avatar_05', label: '鹿', src: avatar05 }),
  Object.freeze({ key: 'avatar_06', label: '水獭', src: avatar06 }),
])

export const CHILD_AVATAR_KEYS = Object.freeze(CHILD_AVATARS.map((avatar) => avatar.key))

export function getChildAvatar(avatarPreset) {
  return CHILD_AVATARS.find((avatar) => avatar.key === avatarPreset) || null
}
