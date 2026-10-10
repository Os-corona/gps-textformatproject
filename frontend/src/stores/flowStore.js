import { defineStore } from 'pinia'

export const useFlowStore = defineStore('flow', {
  state: () => ({
    file: null,
    document: null,
    config: null,
    result: null,
    error: null,
  }),
  actions: {
    setFile(file) {
      this.file = file
    },
    setDocument(document) {
      this.document = document
    },
    setConfig(config) {
      this.config = config
    },
    setResult(result) {
      this.result = result
    },
    setError(error) {
      this.error = error
    },
    reset() {
      this.file = null
      this.document = null
      this.config = null
      this.result = null
      this.error = null
    }
  }
})
