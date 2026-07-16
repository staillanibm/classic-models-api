{{/*
Common labels shared by every resource in this chart.
*/}}
{{- define "classic-models-api.labels" -}}
app.kubernetes.io/part-of: classic-models-api
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{/*
Labels for the API component.
*/}}
{{- define "classic-models-api.apiLabels" -}}
app.kubernetes.io/name: classic-models-api
app.kubernetes.io/instance: classic-models-api
app.kubernetes.io/component: backend
{{ include "classic-models-api.labels" . }}
{{- end -}}

{{/*
Labels for the MySQL component.
*/}}
{{- define "classic-models-api.mysqlLabels" -}}
app.kubernetes.io/name: mysql
app.kubernetes.io/instance: classic-models-mysql
app.kubernetes.io/component: database
{{ include "classic-models-api.labels" . }}
{{- end -}}

{{/*
Look up an existing Secret value by key, falling back to an explicit value,
then to a freshly generated random string. This lets secrets be generated
once on install and preserved across upgrades.
*/}}
{{- define "classic-models-api.secretValue" -}}
{{- $existing := lookup "v1" "Secret" .namespace .secretName -}}
{{- if $existing -}}
  {{- index $existing.data .key | b64dec -}}
{{- else if .explicit -}}
  {{- .explicit -}}
{{- else -}}
  {{- randAlphaNum .length -}}
{{- end -}}
{{- end -}}
