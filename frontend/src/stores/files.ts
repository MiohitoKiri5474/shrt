import { defineStore } from 'pinia'
import { ref } from 'vue'
import { filesApi, type FileOut, type FileKind } from '../api/files'

export const useFilesStore = defineStore('files', () => {
  const files = ref<FileOut[]>([])

  let version = 0

  async function fetchAll() {
    const requestVersion = ++version
    const result = await filesApi.list()
    if (requestVersion === version) {
      files.value = result
    }
  }

  async function upload(file: File, kind: FileKind) {
    const created = await filesApi.upload(file, kind)
    version++
    files.value.unshift(created)
    return created
  }

  async function remove(id: number) {
    await filesApi.remove(id)
    version++
    files.value = files.value.filter((f) => f.id !== id)
  }

  return { files, fetchAll, upload, remove }
})
