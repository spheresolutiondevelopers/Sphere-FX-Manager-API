module sphere-fx-manager-api/go_workers/backtester

go 1.22

require (
    google.golang.org/grpc v1.68.1
    google.golang.org/protobuf v1.35.2
    github.com/spf13/viper v1.19.0
)

replace sphere-fx-manager-api/go_workers/pb => ../pb